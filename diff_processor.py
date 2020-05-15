import re
import os
from git import Repo


class DiffProcessor:
    def __init__(self, project_dir, old_version, new_version, report_dir):
        self.project_dir = project_dir
        self.old_version = old_version
        self.new_version = new_version
        self.report_dir = report_dir
        self.repo = Repo(self.project_dir)

    def resolve_file_info(self, file_name):
        full_path = os.path.join(self.project_dir, file_name)
        package = self.get_package(full_path)
        class_ = re.search('(\w+)\.java$', file_name).group(1)

        is_interface = self.is_interface(full_path)

        return package, class_, is_interface

    def get_package(self, file_name):
        """获取package名"""
        ret = ''
        with open(file_name) as fp:
            for line in fp:
                print("line:{}".format(line))
                line = line.strip()
                match = re.match('package\s+(\S+);', line)
                if match:
                    ret = match.group(1)
                    break
        return ret

    def is_interface(self, file_name):
        """判断某个文件是否是接口"""
        ret = False
        name = re.search('(\w+)\.java$', file_name).group(1)
        reg_interface = re.compile('public\s+interface\s+{}'.format(name))
        with open(file_name) as fp:
            for line in fp:
                line = line.strip()
                match = re.match(reg_interface, line)
                if match:
                    ret = True
                    break
        return ret

    def get_diff(self):
        """获取diff详情"""
        diff = self.repo.git.diff(self.old_version, self.new_version if self.new_version else self.repo.head).split("\n")
        ret = {}

        file_name = ""
        diff_lines = []
        current_line = 0
        for line in diff:
            if line.startswith('diff --git'):
                # 进入新的block
                if file_name != "":
                    ret[file_name] = diff_lines
                file_name = re.findall('b/(\S+)$', line)[0]
                diff_lines = []
                current_line = 0

            elif re.match('@@ -\d+,\d+ \+(\d+),\d+ @@', line):
                match = re.match('@@ -\d+,\d+ \+(\d+),\d+ @@', line)
                current_line = int(match.group(1)) - 1

            elif line.startswith("-"):
                continue
            elif line.startswith("+") and not line.startswith('+++'):
                current_line += 1
                diff_lines.append(current_line)
            else:
                current_line += 1
        ret[file_name] = diff_lines

        return ret

    def modify_html(self, report_dir, package, class_, html_file_name, diff_lines):
        new_line_count, cover_line_count = self.modify_java_html(html_file_name, diff_lines)
        if new_line_count > cover_line_count:
            self.modify_index(report_dir, package, class_)
        return new_line_count, cover_line_count

    def modify_index(self, report_dir, package, class_):
        index_html_path = os.path.join(report_dir, 'index.html')
        with open(index_html_path, 'r') as fp:
            content = fp.readlines()
        for i in range(0, len(content)):
            content[i] = content[i].replace('class="el_package">{}<'.format(package),
                                            'class="el_package-diff" title="Missing change">{}<'.format(package))
        with open(index_html_path, 'w') as fp:
            fp.write("".join(content))

        package_index_html_path = os.path.join(report_dir, package, 'index.html')
        with open(package_index_html_path, 'r') as fp:
            content = fp.readlines()
        for i in range(0, len(content)):
            content[i] = content[i].replace('class="el_class">{}<'.format(class_),
                                            'class="el_class-diff" title="Missing change">{}<'.format(class_))
        with open(package_index_html_path, 'w') as fp:
            fp.write("".join(content))

    def modify_java_html(self, html_file_name, diff_lines):
        new_line_count = 0
        cover_line_count = 0

        with open(html_file_name, 'r') as fp:
            content = fp.readlines()

        for i in range(1, len(content)):
            if i + 1 in diff_lines:
                match = re.search('class="([^"]+)"', content[i])
                if match:
                    content[i] = re.sub('class="([^"]+)"', lambda m: 'class="{}-diff"'.format(m.group(1)), content[i])
                    if re.search('title="([^"]+)"', content[i]):
                        content[i] = re.sub('title="([^"]+)"', lambda m: 'title="{} Missing change"'.format(m.group(1)),
                                            content[i])
                    else:
                        content[i] = re.sub('<span\s(.+?)>',
                                            lambda m: '<span {} title="Missing change">'.format(m.group(1)),
                                            content[i])
                    css_class = match.group(1)
                    new_line_count += 1
                    if css_class.startswith("fc") or css_class.startswith("pc"):
                        cover_line_count += 1

        with open(html_file_name, 'w') as fp:
            fp.write("".join(content))

        return new_line_count, cover_line_count

    def add_total_info(self, report_dir, ret):
        index_html_path = os.path.join(report_dir, 'index.html')
        with open(index_html_path, 'r') as fp:
            content = fp.readlines()
        total = {"difflines": 0, "coveredlines": 0}
        package = {}
        content[0] = re.sub('</a></td>(.+?)</tr>', lambda m: '</a></td>{}<td class="bar" id="diff-hold"/><td '
                                                             'class="ctr2" id="diff-hold">n/a</td></tr>'
                            .format(m.group(1)), content[0])
        for k, v in ret.items():
            package[k] = {"difflines": 0, "coveredlines": 0}
            self.add_package_total_info(report_dir, v, k)
            for ks, vs in v.items():
                package[k]["difflines"] += vs['new']
                package[k]["coveredlines"] += vs['cover']
                total["difflines"] += vs['new']
                total["coveredlines"] += vs['cover']
            cov = package[k]["coveredlines"]
            diff = package[k]["difflines"]
            uncov = diff - cov
            cov_per = int(cov/diff*100)
            content[0] = re.sub('>{}<(.+?)<td class="bar" id="diff-hold"/><td class="ctr2" id="diff-hold">n/a</td>'
                                .format(k), lambda m: '>{}<{}'
                                '<td class="bar"><img src="jacoco-resources/redbar.gif" width="{}" height="10" '
                                'title="{}" alt="{}"/><img src="jacoco-resources/greenbar.gif" width="{}" '
                                'height="10" title="{}" alt="{}"/></td><td class="ctr2">{}%</td>'
                                .format(k, m.group(1), 100-cov_per, uncov, uncov, cov_per, cov, cov, cov_per),
                                content[0])
        cov = total["coveredlines"]
        diff = total["difflines"]
        cov_per = int(cov / diff * 100)
        print("package:{}----total:{}---".format(package, total))
        for i in range(0, len(content)):
            content[i] = content[i].replace('</tr></thead>',
                                            '<td class="down sortable bar" id="n" onclick="toggleSort(this)">Missed '
                                            'Diff-lines</td><td class="sortable ctr2" id="o" onclick="toggleSort('
                                            'this)">Cov.</td></tr></thead>')
            content[i] = content[i].replace('</tr></tfoot>', '<td class="bar">{} of {}</td><td class="ctr2">'
                                                             '{}%</td></tr></tfoot>'.format(cov, diff, cov_per))

        with open(index_html_path, 'w') as fp:
            fp.write("".join(content))

    def add_package_total_info(self, report_dir, ret, package):
        index_html_path = os.path.join(report_dir, package, 'index.html')
        with open(index_html_path, 'r') as fp:
            content = fp.readlines()
        total = {"difflines": 0, "coveredlines": 0}
        content[0] = re.sub('</a></td>(.+?)</tr>', lambda m: '</a></td>{}<td class="bar" id="diff-hold"/><td '
                                                             'class="ctr2" id="diff-hold">n/a</td></tr>'
                            .format(m.group(1)), content[0])
        for k, v in ret.items():
            cov = v['cover']
            diff = v['new']
            uncov = diff - cov
            cov_per = int(cov / diff * 100)
            total["difflines"] += diff
            total["coveredlines"] += cov

            content[0] = re.sub('>{}<(.+?)<td class="bar" id="diff-hold"/><td class="ctr2" id="diff-hold">n/a</td>'
                                .format(k), lambda m: '>{}<{}'
                                '<td class="bar"><img src="../jacoco-resources/redbar.gif" width="{}" height="10" '
                                'title="{}" alt="{}"/><img src="../jacoco-resources/greenbar.gif" width="{}" '
                                'height="10" title="{}" alt="{}"/></td><td class="ctr2">{}%</td>'
                                .format(k, m.group(1), 100-cov_per, uncov, uncov, cov_per, cov, cov, cov_per),
                                content[0])
        cov = total["coveredlines"]
        diff = total["difflines"]
        cov_per = int(cov / diff * 100)
        print("package:{}----total:{}---".format(package, total))
        for i in range(0, len(content)):
            content[i] = content[i].replace('</tr></thead>',
                                            '<td class="down sortable bar" id="n" onclick="toggleSort(this)">Missed '
                                            'Diff-lines</td><td class="sortable ctr2" id="o" onclick="toggleSort('
                                            'this)">Cov.</td></tr></thead>')
            content[i] = content[i].replace('</tr></tfoot>', '<td class="bar">{} of {}</td><td class="ctr2">'
                                                             '{}%</td></tr></tfoot>'.format(cov, diff, cov_per))

        with open(index_html_path, 'w') as fp:
            fp.write("".join(content))

    def process_diff(self):
        ret = {}
        diff_result = self.get_diff()

        for file_name in diff_result:
            # 过滤掉只有删除，没有新增的代码
            if not diff_result[file_name]:
                continue

            # 过滤掉非 java 文件和测试代码
            if not file_name.endswith(".java") or 'src/test/java/' in file_name:
                continue

            package, class_, is_interface = self.resolve_file_info(file_name)
            # 过滤掉接口和非指定的module
            if is_interface:
                continue

            html_file_name = os.path.join(self.report_dir, package, "{}.java.html".format(class_))

            new_line_count, cover_line_count = self.modify_html(self.report_dir, package, class_, html_file_name, diff_result[file_name])
            print("package {}, class {}, 新增 {} 行, 覆盖 {} 行".format(package, class_, new_line_count, cover_line_count))

            # 信息存进返回值
            if package not in ret:
                ret[package] = {}
            ret[package][class_] = {"new": new_line_count, "cover": cover_line_count}

        print(ret)
        self.add_total_info(self.report_dir, ret)

        return ret
