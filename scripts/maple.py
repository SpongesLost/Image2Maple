import subprocess
from xml.etree import ElementTree as ET
from tkinter import messagebox
import os
import logging
import tempfile

def repair_mathml(mathml_str: str) -> str:
    ns = {'m': 'http://www.w3.org/1998/Math/MathML'}
    ET.register_namespace('', ns['m'])
    root = ET.fromstring(mathml_str)

    parent_map = {c: p for p in root.iter() for c in p}

    differential_confirmed = None

    def get_ancestors(element):
        ancestors = []
        parent = parent_map.get(element)
        while parent is not None:
            ancestors.append(parent)
            parent = parent_map.get(parent)
        return ancestors

    def is_differential_d(parent, index):
        if index + 1 >= len(parent):
            return False
            
        current = parent[index]
        next_elem = parent[index + 1]
        
        if (current.tag.endswith('mi') and current.text == 'd' and
            next_elem.tag.endswith('mi') and len(next_elem.text) == 1 and
            next_elem.text.isalpha()):
            
            if parent.tag.endswith('mfrac'):
                numerator = parent[0]
                return current in numerator.findall('.//m:mi', ns)
            
            ancestors = get_ancestors(parent)
            if any(ancestor.tag.endswith('msubsup') and 
                len(ancestor) > 0 and ancestor[0].text == '∫' 
                for ancestor in ancestors):
                return True
                
            return True
            
        return False

    def process_node(parent):
        nonlocal differential_confirmed
        i = 0
        while i < len(parent):
            child = parent[i]
            tag = child.tag.split('}')[-1]

            if tag == 'mi' and child.text == 'd':
                if is_differential_d(parent, i):
                    if differential_confirmed is None:
                        msg = messagebox.askyesno(
                            'Potential Differential',
                            'Detected d[var] in equation. Is this a differential?'
                        )
                        differential_confirmed = msg
                    
                    if differential_confirmed:
                        next_elem = parent[i + 1]
                        d_mo = ET.Element(f"{{{ns['m']}}}mo")
                        d_mo.text = '&DifferentialD;'
                        
                        parent.remove(child)
                        parent.remove(next_elem)
                        parent.insert(i, d_mo)
                        parent.insert(i + 1, next_elem)
                        i += 2
                        continue

            # Case 1: Handle summation operators with complex subscripts
            if tag == 'msub':
                mo = child.find('m:mo', ns)
                if mo is not None and mo.text in ('∑', '∏'):
                    subscript = child.find('m:mrow', ns)
                    if subscript is not None:
                        munderover = ET.Element(f"{{{ns['m']}}}munderover")
                        munderover.append(mo)
                        
                        new_under = ET.Element(f"{{{ns['m']}}}mrow")
                        
                        for elem in subscript:
                            if elem.tag.endswith('mo') and elem.text == '∈':
                                elem.text = '∈'
                            elif elem.tag.endswith('msub'):
                                base = elem.find('m:mi', ns)
                                sub = elem.find('m:mi', ns)
                                if base is not None and sub is not None:
                                    new_msub = ET.Element(f"{{{ns['m']}}}msub")
                                    new_msub.append(base)
                                    new_msub.append(sub)
                                    new_under.append(new_msub)
                                    continue
                            new_under.append(elem)
                        
                        munderover.append(new_under)

                        over = ET.Element(f"{{{ns['m']}}}mo")
                        over.text = ''
                        munderover.append(over)
                        
                        parent.remove(child)
                        parent.insert(i, munderover)
                        i += 1
                        continue

            # Case 2: Handle summation with multiple subscripts (i,j=1)
            if tag == 'msubsup' and len(child) >= 3:
                mo = child.find('m:mo', ns)
                if mo is not None and mo.text in ('∑', '∏'):
                    sub = child[1]
                    sup = child[2]
                    
                    munderover = ET.Element(f"{{{ns['m']}}}munderover")
                    munderover.append(mo)
                    
                    if sub.tag.endswith('mrow'):
                        new_under = ET.Element(f"{{{ns['m']}}}mrow")
                        
                        for elem in sub:
                            if elem.tag.endswith('mo') and elem.text == ',':
                                comma = ET.Element(f"{{{ns['m']}}}mo")
                                comma.text = ','
                                new_under.append(comma)
                                sep = ET.Element(f"{{{ns['m']}}}mo")
                                sep.text = '⁣'
                                new_under.append(sep)
                            else:
                                new_under.append(elem)
                        
                        munderover.append(new_under)
                    else:
                        munderover.append(sub)
                        
                    munderover.append(sup)
                    parent.remove(child)
                    parent.insert(i, munderover)
                    i += 1
                    continue

            # Case 3: Handle hat notation (ψ with ^)
            if tag == 'mover':
                base = child.find('m:mi', ns)
                over = child.find('m:mo', ns)
                if base is not None and over is not None and over.text == '^':
                    new_mover = ET.Element(f"{{{ns['m']}}}mover")
                    new_mover.append(base)
                    
                    hat = ET.Element(f"{{{ns['m']}}}mo")
                    hat.text = '^'
                    new_mover.append(hat)
                    
                    parent.remove(child)
                    parent.insert(i, new_mover)
                    i += 1
                    continue

            # Case 4: Handle square brackets in subscripts (Q[ij])
            if tag == 'msub':
                base = child.find('m:mi', ns)
                sub = child.find('m:mrow', ns)
                if base is not None and sub is not None:
                    if any(elem.tag.endswith('mo') and elem.text in ('[', ']') for elem in sub):
                        new_sub = ET.Element(f"{{{ns['m']}}}mrow")
                        for elem in sub:
                            if elem.tag.endswith('mo') and elem.text == '[':
                                lbrack = ET.Element(f"{{{ns['m']}}}mo")
                                lbrack.text = '['
                                new_sub.append(lbrack)
                            elif elem.tag.endswith('mo') and elem.text == ']':
                                rbrack = ET.Element(f"{{{ns['m']}}}mo")
                                rbrack.text = ']'
                                new_sub.append(rbrack)
                            else:
                                new_sub.append(elem)
                        
                        new_msub = ET.Element(f"{{{ns['m']}}}msub")
                        new_msub.append(base)
                        new_msub.append(new_sub)
                        
                        parent.remove(child)
                        parent.insert(i, new_msub)
                        i += 1
                        continue

            # Case 5: Handle trigonometric functions (cos)
            if tag == 'mi' and child.text in ('cos', 'sin', 'tan'):
                child.text = child.text + ' '
                i += 1
                continue

            # Case 6: Handle parentheses in function arguments
            if tag == 'mo' and child.text in ('(', ')'):
                if child.text == '(':
                    child.text = ' ( '
                else:
                    child.text = ' ) '
                i += 1
                continue

            # Case 7: Handle plus-minus symbol (±)
            if tag == 'mo' and child.text == '±':
                child.text = '∓' if 'minusplus' in mathml_str else '±'
                i += 1
                continue
            
            process_node(child)
            i += 1

    parent_map = {}
    for parent in root.iter():
        for child in parent:
            parent_map[child] = parent

    process_node(root)        
    return ET.tostring(root, encoding='unicode')

def latex_to_mathml(latex, maple_exe, raw: bool = False) -> str:
    cmd = latex.replace('"', '\"')
    cmd = cmd.replace('\\', '\\\\')
    script = f'L:="{cmd}":; MathML:-FromLatex(L); quit;'
    with tempfile.NamedTemporaryFile('w+', suffix='.mpl', delete=False) as f:
        f.write(script)
    proc = subprocess.run([maple_exe, '-q', f.name], capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    os.unlink(f.name)
    if proc.returncode or '<math' not in proc.stdout:
        logging.error(proc.stderr)
        raise RuntimeError('Maple conversion failed')
    out = proc.stdout
    if raw:
        return out[out.find('<math'):out.rfind('</math>') + 7]
    else:
        return repair_mathml(out[out.find('<math'):out.rfind('</math>') + 7])
