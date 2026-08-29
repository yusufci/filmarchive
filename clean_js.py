import re

html_path = '/root/filmarchive/templates/gallery.html'
with open(html_path, 'r', encoding='utf-8') as f:
    content = f.read()

ids_to_remove_js = [
    'rouletteButton', 'marathonButton', 'ambientBtn', 'compareBtn', 
    'closeRouletteModal', 'rouletteSourceTmdb', 'rouletteSourceImdb', 'rouletteSourceArchive',
    'spinAgainBtn', 'rouletteActionBtn',
    'closeTrailerBtn', 'closeTicketBtn', 'copyTicketTextBtn',
    'closePersonBtn', 'closeMarathonBtn', 'marathonRerollBtn',
    'closeAmbientBtn', 'ambientTrailerBtn', 'ambientDetailBtn', 'ambientPrevBtn', 'ambientNextBtn',
    'closeCompareBtn', 'compareSelect1', 'compareSelect2',
    'ticketModal', 'rouletteModal', 'marathonModal', 'ambientModal', 'compareModal'
]

# We should ideally remove any block of code that references these, but a safer approach is to replace 
# document.getElementById('xxx') with (document.getElementById('xxx') || {addEventListener: function(){}, classList: {add: function(){}, remove: function(){}, toggle: function(){}}})
# Wait, this might be tricky if it's assigned to a variable. Let's just do a simpler fix for event listeners.
# We will do a generic replacement for the JS part. Let's just find "document.getElementById('ID')"
# Actually, let's see if we can find them in gallery.html JS.

# For now, let's just make getElementById resilient in the HTML file by overriding it at the start of the script:
# <script>
# const originalGetElementById = document.getElementById.bind(document);
# document.getElementById = function(id) {
#    return originalGetElementById(id) || { addEventListener: () => {}, classList: { add: () => {}, remove: () => {}, toggle: () => {} }, style: {}, setAttribute: () => {}, innerHTML: '', innerText: '', textContent: '', value: '' };
# };
# ...
