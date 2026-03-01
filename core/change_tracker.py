import git
import os
import re


class ChangeTracker:
    def __init__(self, repo_path):
        self.active = False
        self.repo_path = repo_path
        if not os.path.exists(os.path.join(repo_path, '.git')):
            self.repo = git.Repo.init(repo_path)
        else:
            self.repo = git.Repo(repo_path)

    def write_changes(self, file_name, content):
        file_path = os.path.join(self.repo_path, file_name)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)

    def write_change_log(self, path, file_name, readable=False):
        diff = self.repo.git.diff('HEAD', '--word-diff=plain', '--histogram', '--unified=10000', '--', file_name)
        diff_lines = diff.split('\n')
        content = diff_lines[5:]
        write_lines = []
        print('content', content)
        if readable:
            for line in content:
                title = ''
                print(line)
                if '<D=' in line:
                    try:
                        div = re.match(r'<D=\.([0-9a-zA-Z]+)\.([a-zA-Z]+)', line)
                        name = div.group(1)
                        subtype = div.group(2)
                        title = f'#{subtype} {name}'
                    except AttributeError:
                        div = re.match(r'<D=\.([0-9a-zA-Z])+', line)
                        if div:
                            super_div = div.group(1)
                            title = f'##{super_div}'
                else:
                    try:
                        match = re.match(r'^(\[-)?\(?([0-9]+)', line)
                        line_n = match.group(2)
                    except AttributeError:
                        line_n = ''
                    if line_n:
                        title = line_n
                changes = []
                del_pattern = r'\[-(.*?)-]'
                add_pattern = r'\{\+(.*?)\+}'
                replacements = re.findall(del_pattern + add_pattern, line)
                for replacement in replacements:
                    changes.append(f'{replacement[0]} > {replacement[1]}')
                    line = line.replace(f'[-{replacement[0]}-]{{+{replacement[1]}+}}', '')
                deletions = re.findall(del_pattern, line)
                additions = re.findall(add_pattern, line)
                for deletion in deletions:
                    changes.append(f'delete {deletion}')
                for addition in additions:
                    changes.append(f'add {addition}')
                print(title, changes)
                if changes:
                    if title:
                        line = title + ': ' + ' || '.join(changes)
                    else:
                        line = ' || '.join(changes)
                    write_lines.append(line)
                elif '#' in title:
                    write_lines.append(title)
        else:
            write_lines = content
        text = '\n'.join(write_lines)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
        return text

    def parse_word_diff(self, file_name):
        diff = self.repo.git.diff('HEAD', '--word-diff=plain', '--histogram', '--unified=10000', '--', file_name)
        lines = diff.splitlines()
        lines = lines[5:]
        pattern = re.compile(r'\[-(.*?)-]|\{\+(.*?)\+}|([^{}\[\]\n]+)')
        result = []
        for line in lines:
            parts = []
            for match in pattern.finditer(line):
                deletion, addition, normal = match.groups()
                if deletion is not None:
                    parts.append((-1, deletion))
                elif addition is not None:
                    parts.append((1, addition))
                elif normal is not None:
                    parts.append((0, normal))
            result.append(parts)
        return result

    def request_active(self, file_name):
        if os.path.exists(os.path.join(self.repo_path, file_name)):
            self.active = True
            return True
        else:
            self.active = False
            return False

    def stop_tracking(self, file_name):
        path = os.path.join(self.repo_path, file_name)
        if os.path.exists(path):
            os.remove(path)
            self.active = False

    def commit_changes(self, message="Initiate tracking"):
        self.repo.git.add(A=True)
        self.repo.index.commit(message)