import re

html_path = '/root/filmarchive/templates/gallery.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Remove the openMobileToolsTopBtn
pattern_top_btn = r'<button\s+id="openMobileToolsTopBtn".*?</button>\s*'
content = re.sub(pattern_top_btn, '', content, flags=re.DOTALL)

# Remove mobileNavTools button
pattern_nav_tools = r'<button\s+id="mobileNavTools".*?</button>\s*'
content = re.sub(pattern_nav_tools, '', content, flags=re.DOTALL)

# Remove the mobileToolsModal itself
start_idx = content.find('<div id="mobileToolsModal"')
if start_idx != -1:
    open_divs = 0
    end_idx = start_idx
    while end_idx < len(content):
        if content[end_idx:end_idx+4] == '<div':
            open_divs += 1
            end_idx += 4
        elif content[end_idx:end_idx+6] == '</div>':
            open_divs -= 1
            end_idx += 6
            if open_divs == 0:
                break
        else:
            end_idx += 1
    content = content[:start_idx] + content[end_idx:]


with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Remaining mobile tools cleaned")
