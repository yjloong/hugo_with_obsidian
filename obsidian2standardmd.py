import datetime
import os
import shutil
from optfunc2 import *
import re

import yaml

static_resources_root = os.path.join(os.path.dirname(__file__), 'static')
res_imgs_root = os.path.join(static_resources_root, 'images')
md_root = os.path.join(os.path.dirname(__file__), 'content/post')

hugo_front_matter = ['title', 
                     'date', 
                     'draft', 
                     'published',
                     'tags', 
                     'categories', 
                     'description', 
                     'author', 
                     'image', 
                     'keywords']

hugo_front_matter_default = {
    "comment": "false",
    "author": "yjloong",
    "omit_header_text": "true",
    "featured_image": "/images/bg01.JPG",
    "toc": "false",
    "reward": "false"
}

# header选用yaml格式，因为obsidian就是用yaml格式的
"""
yaml格式：
---
expiryDate: 2024-10-19T00:32:13-07:00
title: 文章 1
---

toml格式：
+++
expiryDate = 2024-10-19T00:32:13-07:00
title = '文章 1'
+++

json格式：
{
  "expiryDate": "2024-10-19T00:32:13-07:00",
  "title": "文章 1"
}
"""

# date 采用

def find_and_clean_tags(line: str):
    """
    find tags in the line and return them.
    """
    tags = re.findall(r'(?<!\w)#([a-zA-Z0-9_/-]+)', line)
    
    cleaned_line = re.sub(r'(?<!\w)#[a-zA-Z0-9_/-]+\s*', '', line).strip()
    
    return tags, cleaned_line

def convert_obsidian_links(line: str, others: list, dryrun = True):
    """
    The line comes from obsidian format. Find out links in the line and return them.
    fmt1: [[普通链接]]  
    fmt2: [[带别名|别名文本]]  
    fmt3: [[页面#标题]]  
    fmt4: [[页面#^block-id]] 
    """
    
    pattern = r'\[\[([^\]#\|]+)(?:#([^\^\]\|]+))?(?:\^\^?([^\]]+))?(?:\|([^\]]+))?\]\]'

    def replace_match(match):
        target, header, block, alias = match.groups()
        
        for other in others:
            if not os.path.isabs(other):
                raise ValueError(f"{other} is not an absolute path")
            
            if other.endswith(target):
                target = f'{res_imgs_root}/{target}'
                # target exists and newer than other, then not copy
                if os.path.exists(target) and os.path.getmtime(target) > os.path.getmtime(other):
                    pass
                elif dryrun == False:
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    shutil.copy(other, target)
                elif dryrun == True:
                    print(f'[dryrun] copy {other} to {target}')
                
        if alias: # [[target|alias]]
            return f'[{alias}]({target})'
        elif block: # [[target#^block]]
            return f'[{target}#^{header}]({target}#^{block})'
        elif header: # [[target#header]]
            return f'[{target}#{header}]({target}#{header})'
        else:
            return f'[image]({target})'
        
    return re.sub(pattern, replace_match, line)
        

@cmdline
def onefile(md_path: str, others: list, dryrun: bool = True):
    print(f'Converting {md_path} ...')
    with open(md_path, 'r', encoding='utf-8') as f:
        
        in_code_block = False
        in_matter = False
        matter = {}
        new_lines = []
        all_tags = []
        
        # The first line must be starting with ---
        # Must have 'published' tag
        for idx, line in enumerate(f):
            # read the front matter
            if idx == 0 and line.startswith('---'):
                in_matter = True
                continue
            elif idx == 0:
                return # skip the file

            if in_matter:
                yaml_data = yaml.load(line, Loader=yaml.FullLoader)
                if yaml_data:
                    for yaml_key, yaml_value in yaml_data.items():
                        matter[yaml_key] = yaml_value
                
                if line.startswith('---'):
                    in_matter = False
                    if 'published' not in matter and 'draft' not in matter:
                        return
                
                continue

            line = line.strip()

            if '```' in line:
                in_code_block = not in_code_block
                new_lines.append(line)
                continue

            if in_code_block:
                new_lines.append(line)
                continue

            tags, line = find_and_clean_tags(line)
            all_tags += tags
            #tags = [tag.replace('/', '-') for tag in tags]
            
            line = convert_obsidian_links(line, others=others, dryrun=dryrun)
            new_lines.append(line)
        
        if new_lines == []:
            return
        
        # 如果matter中没有时间，则以文件创建时间作为时间
        new_file_path = os.path.join(md_root, os.path.basename(md_path))
        os.makedirs(os.path.dirname(new_file_path), exist_ok=True)
        
        # 将published改为draft
        if 'published' in matter:
            matter['draft'] = not matter['published']
            del matter['published']

        for def_key in hugo_front_matter_default.keys():
            if def_key not in matter:
                matter[def_key] = hugo_front_matter_default[def_key]

        with open(new_file_path, 'w', encoding='utf-8') as newf:
            newf.write('---\n')
            for k, v in matter.items():
                newf.write(f'{k}: {v}\n')
            if 'date' not in matter:
                # format of date: %Y-%m-%d
                file_created_time = datetime.datetime.fromtimestamp(os.path.getctime(md_path))
                newf.write(f'date: {file_modified_time.strftime("%Y-%m-%d")}\n')
            if 'lastmod' not in matter:
                file_modified_time = datetime.datetime.fromtimestamp(os.path.getmtime(md_path))
                newf.write(f'lastmod: {file_modified_time.strftime("%Y-%m-%d")}\n')
            
            if 'categories' not in matter:
                newf.write('categories: ["nocategory"]\n')
            
            

            # write tags example: tags: ["Hugo", "教程"]
            if len(all_tags):
                newf.write(f'tags: {all_tags}\n')
            
            newf.write('---\n')
            newf.writelines([line + '\n' for line in new_lines])

        print(f'{matter = } {all_tags = }')
                
                
@cmdline_default
def conv(obsidian_dir: str = '/mnt/c/Users/bajeer/Documents/obsidian/'):
    mds = []
    others = []
    ignore_dirs = ['.trash', '.git']
    
    for root, dirs, files in os.walk(obsidian_dir):
        dirs[:] = [
            d for d in dirs
            if d not in ignore_dirs and not d.startswith('.')
        ]

        for file in files:
            if file.startswith('.'):
                continue

            if file.endswith('.md'):
                mds.append(os.path.join(root, file))
            else:
                others.append(os.path.join(root, file))
    
    for md in mds:
        onefile(md, others, False)

@cmdline
def test_yaml():
    test_lines = [
        "name: Alice"
    ]
    for line in test_lines:
        print(yaml.safe_load(line))

if __name__ == '__main__':
    cmdline_start(globals=globals(), has_abbrev=True)
