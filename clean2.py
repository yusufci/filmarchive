import re

html_path = '/root/filmarchive/templates/gallery.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

buttons_to_remove = [
    'mobileToolRoulette', 'mobileToolMarathon', 'mobileToolAmbient', 'mobileToolCompare'
]

for btn in buttons_to_remove:
    pattern = r'<button\s+id="' + btn + r'".*?</button>\s*'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Mobile tools cleaned")
