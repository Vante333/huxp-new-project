import json
import re
import os

def get_children(topic):
    return topic.get('children', {}).get('attached', [])

def clean_title(title):
    return title.replace('\n', ' ').strip()

def is_url(text):
    return text.strip().startswith('http')

def extract_priority(title):
    match = re.search(r'tc-P(\d)', title)
    if match:
        return int(match.group(1))
    return None

def is_result_marker(title):
    t = title.strip()
    return bool(re.match(r'tc-P\d[:：]\s*预期结果', t)) or t == '预期结果' or t.startswith('预期结果')

def is_tc_node(title):
    return bool(re.search(r'tc-P\d', title)) and not is_result_marker(title)

def strip_tc_prefix(text):
    return re.sub(r'^tc-P\d[:：]\s*', '', text).strip()


def collect_all_results(topic):
    """Collect expected results from a test case node, handling various patterns."""
    results = []
    children = get_children(topic)
    
    for child in children:
        ct = clean_title(child.get('title', ''))
        if is_url(ct):
            continue
        
        gc = get_children(child)
        
        if is_result_marker(ct):
            for sub in gc:
                st = clean_title(sub.get('title', ''))
                if not is_url(st):
                    results.append(strip_tc_prefix(st))
                    for ssub in get_children(sub):
                        sst = clean_title(ssub.get('title', ''))
                        if not is_url(sst):
                            results.append(strip_tc_prefix(sst))
        elif not gc or all(is_url(clean_title(g.get('title', ''))) for g in gc):
            results.append(strip_tc_prefix(ct))
        else:
            has_rm = any(is_result_marker(clean_title(g.get('title', ''))) for g in gc)
            if has_rm:
                for g in gc:
                    gt = clean_title(g.get('title', ''))
                    if is_result_marker(gt):
                        for sg in get_children(g):
                            sgt = clean_title(sg.get('title', ''))
                            if not is_url(sgt):
                                results.append(strip_tc_prefix(sgt))
                    elif not is_url(gt):
                        results.append(strip_tc_prefix(gt))
            else:
                results.append(strip_tc_prefix(ct))
                for g in gc:
                    gt = clean_title(g.get('title', ''))
                    if not is_url(gt):
                        ggc = get_children(g)
                        if not ggc or all(is_url(clean_title(x.get('title', ''))) for x in ggc):
                            results.append(strip_tc_prefix(gt))
    
    return [r for r in results if r and not is_url(r)]


def derive_module_abbr(title):
    t = title.lower()
    if 'membership' in t or '充点' in title or '权益支持' in title:
        return 'MBR'
    elif '搜索' in title and '聚合' in title:
        return 'SEARCH'
    elif 'premium' in t or '等级打标' in title:
        return 'TIER'
    elif 'e-pass' in t or 'epass' in t:
        return 'EPASS'
    elif 'migration' in t or 'order list' in t:
        return 'ORDER'
    elif '可用资源' in title:
        return 'RES'
    return 'GEN'


def derive_sub_abbr(title, parent_abbr):
    t = title.lower()
    mappings = [
        ('lounge', 'LNG'), ('esim', 'ESIM'), ('setmeal', 'SET'), ('套餐', 'SET'),
        ('coupon', 'CPN'), ('fitness', 'FIT'),
        ('编辑权益', 'UPD'), ('entitlements/update', 'UPD'),
        ('权益查询', 'QRY'), ('entitlements/search', 'QRY'),
        ('充值流程', 'RCH'), ('充值', 'RCH'),
        ('会籍模板', 'TPL'), ('会籍注册', 'REG'), ('registration', 'REG'),
        ('订单', 'ORD'), ('order', 'ORD'), ('预览', 'PRV'), ('preview', 'PRV'),
        ('预订', 'PBK'), ('prebooking', 'PBK'), ('可用性', 'AVL'), ('availability', 'AVL'),
        ('价格', 'PRC'), ('price', 'PRC'), ('告警', 'ALT'),
        ('缓存', 'CACHE'), ('搜索', 'SCH'), ('资源', 'RES'),
        ('模板', 'TPL'), ('参数', 'PARAM'), ('数值', 'VAL'),
        ('共享', 'SHARE'), ('状态', 'STS'), ('删除', 'DEL'), ('修改', 'MOD'),
    ]
    
    for keyword, abbr in mappings:
        if keyword in t:
            return abbr
    
    if 'ft' == t.strip():
        return 'FT'
    
    return None


class TestCase:
    def __init__(self, priority, scenario, results, context_path):
        self.priority = priority
        self.scenario = scenario
        self.results = results
        self.context_path = context_path


class MarkdownGeneratorV2:
    def __init__(self):
        self.lines = []
        self.all_test_cases = []
    
    def collect_test_cases(self, topic, path, product_type=''):
        """Recursively collect all test cases with their context paths."""
        title = clean_title(topic.get('title', ''))
        children = get_children(topic)
        
        if not title or title == '子主题 1':
            return
        
        if is_tc_node(title):
            priority = extract_priority(title)
            scenario = strip_tc_prefix(title)
            if not scenario:
                scenario = title
            results = collect_all_results(topic)
            self.all_test_cases.append(TestCase(priority, scenario, results, list(path)))
            return
        
        has_result_child = any(is_result_marker(clean_title(c.get('title', ''))) for c in children)
        if has_result_child:
            priority = extract_priority(title)
            result_child = next(c for c in children if is_result_marker(clean_title(c.get('title', ''))))
            if priority is None:
                priority = extract_priority(clean_title(result_child.get('title', '')))
            if priority is None:
                priority = 1
            scenario = strip_tc_prefix(title)
            if not scenario:
                scenario = title
            
            results = []
            for child in children:
                ct = clean_title(child.get('title', ''))
                if is_url(ct):
                    continue
                if is_result_marker(ct):
                    for sub in get_children(child):
                        st = clean_title(sub.get('title', ''))
                        if not is_url(st):
                            results.append(strip_tc_prefix(st))
                            for ssub in get_children(sub):
                                sst = clean_title(ssub.get('title', ''))
                                if not is_url(sst):
                                    results.append(strip_tc_prefix(sst))
                else:
                    results.append(strip_tc_prefix(ct))
            
            results = [r for r in results if r and not is_url(r)]
            self.all_test_cases.append(TestCase(priority, scenario, results, list(path)))
            return
        
        new_path = path + [title]
        for child in children:
            self.collect_test_cases(child, new_path)
    
    def generate(self, data):
        root = data[0]['rootTopic']
        root_title = clean_title(root['title'])
        
        d1_children = get_children(root)
        
        for d1 in d1_children:
            d1_title = clean_title(d1.get('title', ''))
            if not d1_title or d1_title == '子主题 1':
                continue
            
            module_abbr = derive_module_abbr(d1_title)
            self.all_test_cases = []
            self.collect_test_cases(d1, [d1_title])
            
            if not self.all_test_cases:
                continue
            
            grouped = self.group_test_cases(d1_title)
            self.emit_section(root_title, d1_title, module_abbr, grouped)
        
        return '\n'.join(self.lines)
    
    def group_test_cases(self, h2_title):
        groups = {}
        for tc in self.all_test_cases:
            path = tc.context_path
            
            effective_path = [p for p in path if p != h2_title]
            if not effective_path:
                effective_path = ['通用验证']
            
            if len(effective_path) >= 2:
                h3_key = effective_path[0]
                h4_key = effective_path[1]
            elif len(effective_path) == 1:
                h3_key = effective_path[0]
                h4_key = ''
            else:
                h3_key = '通用验证'
                h4_key = ''
            
            if h3_key not in groups:
                groups[h3_key] = {}
            if h4_key not in groups[h3_key]:
                groups[h3_key][h4_key] = []
            groups[h3_key][h4_key].append(tc)
        
        return groups
    
    def emit_section(self, root_title, h2_title, module_abbr, grouped):
        if not self.lines:
            self.lines.append(f"# {root_title} 测试用例")
            self.lines.append('')
        
        self.lines.append(f"## {h2_title}")
        self.lines.append('')
        
        tc_counter = {}
        
        for h3_title, h4_groups in grouped.items():
            h3_display = strip_tc_prefix(h3_title)
            if not h3_display or is_url(h3_display):
                continue
            
            self.lines.append(f"### {h3_display}")
            self.lines.append('')
            
            sub_abbr = derive_sub_abbr(h3_title, module_abbr)
            h3_abbr = f"{module_abbr}-{sub_abbr}" if sub_abbr else module_abbr
            
            for h4_title, test_cases in h4_groups.items():
                if h4_title:
                    h4_display = strip_tc_prefix(h4_title)
                    if h4_display and not is_url(h4_display):
                        self.lines.append(f"#### {h4_display}")
                        self.lines.append('')
                        h4_sub = derive_sub_abbr(h4_title, h3_abbr)
                        tc_abbr = f"{h3_abbr}-{h4_sub}" if h4_sub and h4_sub != sub_abbr else h3_abbr
                    else:
                        tc_abbr = h3_abbr
                else:
                    tc_abbr = h3_abbr
                
                parts = tc_abbr.split('-')
                if len(parts) > 3:
                    seen = []
                    for p in parts:
                        if p not in seen:
                            seen.append(p)
                    tc_abbr = '-'.join(seen[:3])
                
                for tc in test_cases:
                    p = tc.priority if tc.priority is not None else 1
                    counter_key = f"P{p}-{tc_abbr}"
                    if counter_key not in tc_counter:
                        tc_counter[counter_key] = 0
                    tc_counter[counter_key] += 1
                    tc_id = f"tc-P{p}-{tc_abbr}-{tc_counter[counter_key]:03d}"
                    
                    self.lines.append(f"##### {tc_id}：{tc.scenario}")
                    self.lines.append('')
                    
                    if tc.results:
                        for r in tc.results:
                            if r and not is_url(r):
                                self.lines.append(f"- tc-P{p}: {r}")
                    
                    self.lines.append('')


def main():
    with open('tools/xmind_content.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    gen = MarkdownGeneratorV2()
    output = gen.generate(data)
    
    output = re.sub(r'\n{3,}', '\n\n', output)
    
    output_path = os.path.join('testcases', '2026Q1_SP3-测试用例.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(output)
    
    print(f"Generated: {output_path}")
    print(f"Total lines: {len(output.splitlines())}")
    
    tc_count = len(re.findall(r'^##### tc-', output, re.MULTILINE))
    p0_count = len(re.findall(r'^##### tc-P0', output, re.MULTILINE))
    p1_count = len(re.findall(r'^##### tc-P1', output, re.MULTILINE))
    p2_count = len(re.findall(r'^##### tc-P2', output, re.MULTILINE))
    total = p0_count + p1_count + p2_count
    print(f"\nTotal test cases: {tc_count}")
    print(f"  P0: {p0_count} ({p0_count/max(total,1)*100:.1f}%)")
    print(f"  P1: {p1_count} ({p1_count/max(total,1)*100:.1f}%)")
    print(f"  P2: {p2_count} ({p2_count/max(total,1)*100:.1f}%)")
    
    long_ids = re.findall(r'##### (tc-[^\s：]+)', output)
    max_len = max(len(x) for x in long_ids) if long_ids else 0
    long_ones = [x for x in long_ids if len(x) > 30]
    if long_ones:
        print(f"\nWarning: {len(long_ones)} IDs longer than 30 chars (max: {max_len})")
        for x in long_ones[:5]:
            print(f"  {x}")


if __name__ == '__main__':
    main()
