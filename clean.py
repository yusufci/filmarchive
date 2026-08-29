import re

html_path = '/root/filmarchive/templates/gallery.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Emojis to remove explicitly
emojis = [
    '🎬', '📊', '🎲', '🍿', '📽️', '⚖️', '📥', '⌨️', '🌙', '🔄', '⚡', '❤️', '★', '⏳', '✓', 
    '🧠', '🚀', '🕯️', '⚡', '🏛️', '🖼️', '📋', '📌', '📅', '⭐', '🎭', '🏆', '🛠️', '🧹', '💾',
    '🎬', '▶️', '🎵', 'ℹ️', '⏱️', '🌟', '📂', '🎯'
]

# Remove emojis, replace with empty string
for e in emojis:
    content = content.replace(e + ' ', '')
    content = content.replace(e, '')

# Remove AI generated buttons from the header (Desktop & Mobile)
# Look for button by id
buttons_to_remove = [
    'rouletteButton', 'marathonButton', 'ambientBtn', 'compareBtn'
]

for btn in buttons_to_remove:
    # Use regex to remove the entire <button id="...">...</button> tag
    # This might span multiple lines
    pattern = r'<button\s+id="' + btn + r'".*?</button>\s*'
    content = re.sub(pattern, '', content, flags=re.DOTALL)

# Remove modals
modals_to_remove = [
    'rouletteModal', 'marathonModal', 'ambientModal', 'compareModal', 'ticketModal'
]

for modal in modals_to_remove:
    # We will find the div with this id and remove it, assuming it ends before the next modal or </body>
    # Since regex for HTML is hard, let's use a simple approach:
    # We find '<div id="modalID"' and then find the corresponding closing </div>
    start_idx = content.find(f'<div id="{modal}"')
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

print("HTML cleaned")
