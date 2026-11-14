"""
SpinSleeve V2 Music Legend Illustrated Avatars Service (`services/avatars.py`)
-----------------------------------------------------------------------------
Houses the 12 curated Music Legend avatar presets and high-fidelity vector SVG strings (APP-04).
"""

AVATAR_PRESETS = [
    {"id": "beethoven", "name": "Ludwig van Beethoven", "era": "Classical", "badge": "🎹", "desc": "Romantic & classical titan"},
    {"id": "chet_baker", "name": "Chet Baker", "era": "Cool Jazz", "badge": "🎺", "desc": "West Coast jazz noir"},
    {"id": "miles_davis", "name": "Miles Davis", "era": "Modal Jazz", "badge": "🕶️", "desc": "Kind of Blue trumpet legend"},
    {"id": "bob_dylan", "name": "Bob Dylan", "era": "Folk / 60s", "badge": "🎸", "desc": "Counterculture poet"},
    {"id": "david_bowie", "name": "David Bowie", "era": "Glam Rock", "badge": "⚡", "desc": "Aladdin Sane chameleon"},
    {"id": "stevie_wonder", "name": "Stevie Wonder", "era": "Soul & Funk", "badge": "🎹", "desc": "Motown visionary"},
    {"id": "jimi_hendrix", "name": "Jimi Hendrix", "era": "Psychedelic Rock", "badge": "🎸", "desc": "Voodoo child virtuoso"},
    {"id": "fela_kuti", "name": "Fela Kuti", "era": "Afrobeat", "badge": "🎷", "desc": "Afrobeat pioneer & activist"},
    {"id": "madonna", "name": "Madonna", "era": "80s Pop", "badge": "👑", "desc": "Queen of Pop & reinvention"},
    {"id": "amy_winehouse", "name": "Amy Winehouse", "era": "Neo-Soul", "badge": "🎤", "desc": "Camden beehive & jazz voice"},
    {"id": "daft_punk", "name": "Daft Punk", "era": "French House", "badge": "🤖", "desc": "Chrome helmet electronic duo"},
    {"id": "drake", "name": "Drake", "era": "Hip-Hop / R&B", "badge": "🦉", "desc": "Certified Lover Boy & OVO"}
]

AVATAR_SVGS = {
    "beethoven": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-beethoven" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#334155"/>
      <stop offset="100%" stop-color="#0f172a"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-beethoven)" stroke="#64748b" stroke-width="2"/>
  <path d="M22 56 C14 42 16 26 30 18 C40 12 60 12 70 18 C84 26 86 42 78 56 C82 46 80 30 68 22 C58 16 42 16 32 22 C20 30 18 46 22 56 Z" fill="#cbd5e1"/>
  <path d="M18 48 C14 36 22 24 34 20 C24 26 22 38 24 50 Z" fill="#94a3b8"/>
  <path d="M82 48 C86 36 78 24 66 20 C76 26 78 38 76 50 Z" fill="#94a3b8"/>
  <path d="M34 38 Q50 34 66 38 Q68 56 62 68 Q50 76 38 68 Q32 56 34 38 Z" fill="#fed7aa"/>
  <path d="M40 45 Q46 44 49 47" stroke="#334155" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M60 45 Q54 44 51 47" stroke="#334155" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <circle cx="45" cy="50" r="2" fill="#1e293b"/>
  <circle cx="55" cy="50" r="2" fill="#1e293b"/>
  <path d="M50 48 L48 57 L52 57" stroke="#ea580c" stroke-width="1.5" stroke-linecap="round" fill="none"/>
  <path d="M44 63 Q50 62 56 63" stroke="#9a3412" stroke-width="2" stroke-linecap="round"/>
  <polygon points="26,96 32,72 42,76 36,96" fill="#e2e8f0"/>
  <polygon points="74,96 68,72 58,76 64,96" fill="#e2e8f0"/>
  <polygon points="40,73 50,82 60,73 55,96 45,96" fill="#ffffff" stroke="#cbd5e1" stroke-width="1"/>
  <polygon points="22,96 30,72 18,80 14,96" fill="#1e293b"/>
  <polygon points="78,96 70,72 82,80 86,96" fill="#1e293b"/>
  <rect x="36" y="92" width="28" height="6" rx="1" fill="#ffffff"/>
  <rect x="41" y="92" width="3" height="4" fill="#0f172a"/>
  <rect x="47" y="92" width="3" height="4" fill="#0f172a"/>
  <rect x="56" y="92" width="3" height="4" fill="#0f172a"/>
</svg>""",

    "chet_baker": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-chet" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#050515"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-chet)" stroke="#4338ca" stroke-width="2"/>
  <path d="M28 36 C28 20 40 16 56 16 C70 16 76 24 76 36 C76 40 70 30 56 26 C40 22 30 30 28 36 Z" fill="#1e293b"/>
  <path d="M34 36 C38 28 58 26 66 34 C72 40 72 54 66 64 C60 72 48 72 40 68 L36 54 Z" fill="#fed7aa"/>
  <path d="M44 42 Q50 40 54 43" stroke="#312e81" stroke-width="2" stroke-linecap="round" fill="none"/>
  <circle cx="50" cy="45" r="2" fill="#1e1b4b"/>
  <path d="M58 52 C54 58 48 62 42 63" stroke="#d97706" stroke-width="1.5" fill="none" opacity="0.6"/>
  <polygon points="46,54 20,62 18,68 48,57" fill="#f59e0b" stroke="#d97706" stroke-width="1"/>
  <rect x="28" y="57" width="3" height="7" fill="#fbbf24"/>
  <rect x="33" y="55" width="3" height="7" fill="#fbbf24"/>
  <rect x="38" y="53" width="3" height="7" fill="#fbbf24"/>
  <polygon points="18,56 8,52 6,72 18,68" fill="#fbbf24" stroke="#d97706" stroke-width="1.5"/>
  <ellipse cx="7" cy="62" rx="2" ry="10" fill="#f59e0b"/>
  <path d="M6 55 Q-2 62 6 69" stroke="#818cf8" stroke-width="1.5" stroke-linecap="round" fill="none" opacity="0.8"/>
  <path d="M24 96 C24 76 40 72 50 72 C64 72 80 76 80 96 Z" fill="#0f172a"/>
</svg>""",

    "miles_davis": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-miles" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#0369a1"/>
      <stop offset="100%" stop-color="#04182e"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-miles)" stroke="#0284c7" stroke-width="2"/>
  <path d="M36 34 C36 22 46 18 58 18 C70 18 76 26 76 38 C76 52 70 66 58 70 C48 72 38 64 36 50 Z" fill="#451a03"/>
  <rect x="42" y="38" width="26" height="10" rx="2" fill="#0f172a"/>
  <polygon points="45,40 52,40 48,46 43,46" fill="#38bdf8" opacity="0.7"/>
  <polygon points="57,40 64,40 60,46 55,46" fill="#38bdf8" opacity="0.7"/>
  <path d="M22 96 C22 74 38 70 54 70 C70 70 82 74 82 96 Z" fill="#18181b"/>
  <polygon points="48,70 54,84 60,70" fill="#dc2626"/>
  <polygon points="48,56 32,74 28,70 46,52" fill="#eab308" stroke="#ca8a04" stroke-width="1"/>
  <polygon points="32,74 22,84 16,78 28,70" fill="#eab308"/>
  <ellipse cx="19" cy="81" rx="5" ry="7" fill="#dc2626" stroke="#991b1b" stroke-width="1.5"/>
  <circle cx="19" cy="81" r="2.5" fill="#18181b"/>
</svg>""",

    "bob_dylan": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-dylan" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#78350f"/>
      <stop offset="100%" stop-color="#1c0d02"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-dylan)" stroke="#b45309" stroke-width="2"/>
  <path d="M24 44 C18 32 24 16 38 14 C48 12 64 12 72 16 C84 22 86 36 80 48 C84 38 82 24 70 18 C58 14 42 16 30 22 C22 28 20 38 24 44 Z" fill="#451a03"/>
  <circle cx="30" cy="26" r="8" fill="#451a03"/>
  <circle cx="44" cy="18" r="8" fill="#542305"/>
  <circle cx="60" cy="18" r="9" fill="#451a03"/>
  <circle cx="74" cy="28" r="8" fill="#542305"/>
  <path d="M35 34 Q50 30 65 34 Q68 54 62 66 Q50 74 38 66 Q33 54 35 34 Z" fill="#fed7aa"/>
  <rect x="36" y="38" width="13" height="10" rx="2" fill="#18181b"/>
  <rect x="51" y="38" width="13" height="10" rx="2" fill="#18181b"/>
  <rect x="47" y="40" width="6" height="2.5" fill="#18181b"/>
  <path d="M30 82 L34 65 L40 64" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" fill="none"/>
  <path d="M70 82 L66 65 L60 64" stroke="#94a3b8" stroke-width="2" stroke-linecap="round" fill="none"/>
  <rect x="36" y="62" width="28" height="6" rx="1.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1"/>
  <line x1="39" y1="65" x2="61" y2="65" stroke="#475569" stroke-width="1.5" stroke-dasharray="2 2"/>
  <polygon points="22,96 32,78 42,84 38,96" fill="#92400e"/>
  <polygon points="78,96 68,78 58,84 62,96" fill="#92400e"/>
  <polygon points="42,84 50,96 58,84" fill="#1e3a8a"/>
</svg>""",

    "david_bowie": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-bowie" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1e1b4b"/>
      <stop offset="100%" stop-color="#0c0a1f"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-bowie)" stroke="#ec4899" stroke-width="2"/>
  <path d="M24 48 C16 34 22 18 36 14 C48 10 66 12 76 18 C86 26 84 42 78 52 C74 38 68 20 50 18 C34 18 26 32 24 48 Z" fill="#f97316"/>
  <polygon points="30,18 36,8 44,16 52,8 60,16 68,10 70,20" fill="#ea580c"/>
  <path d="M34 34 Q50 30 66 34 Q68 56 60 70 Q50 78 40 70 Q32 56 34 34 Z" fill="#ffedd5"/>
  <polygon points="54,22 62,38 54,44 66,66 58,54 62,46 50,24" fill="#06b6d4"/>
  <polygon points="52,22 60,38 52,44 64,66 56,54 60,46 48,24" fill="#ef4444"/>
  <path d="M39 46 Q44 43 48 46" stroke="#475569" stroke-width="1.8" fill="none"/>
  <circle cx="43" cy="48" r="2.2" fill="#0284c7"/>
  <path d="M45 66 Q50 68 55 66" stroke="#e11d48" stroke-width="2.5" stroke-linecap="round"/>
  <path d="M20 96 C24 78 38 74 50 74 C62 74 76 78 80 96 Z" fill="#0f172a"/>
  <polygon points="42,74 50,86 58,74" fill="#f43f5e"/>
  <circle cx="50" cy="74" r="3" fill="#fbbf24"/>
</svg>""",

    "stevie_wonder": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-stevie" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#b45309"/>
      <stop offset="100%" stop-color="#3b1d06"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-stevie)" stroke="#f59e0b" stroke-width="2"/>
  <path d="M26 38 C26 22 36 16 50 16 C64 16 74 22 74 38 Z" fill="#18181b"/>
  <line x1="28" y1="36" x2="24" y2="56" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="24" cy="56" r="2.5" fill="#fbbf24"/>
  <line x1="32" y1="34" x2="28" y2="60" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="28" cy="60" r="2.5" fill="#fbbf24"/>
  <line x1="68" y1="34" x2="72" y2="60" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="72" cy="60" r="2.5" fill="#fbbf24"/>
  <line x1="72" y1="36" x2="76" y2="56" stroke="#18181b" stroke-width="2.5" stroke-linecap="round"/>
  <circle cx="76" cy="56" r="2.5" fill="#fbbf24"/>
  <path d="M33 34 Q50 30 67 34 Q70 56 64 68 Q50 76 36 68 Q30 56 33 34 Z" fill="#78350f"/>
  <rect x="34" y="38" width="14" height="11" rx="3" fill="#18181b" stroke="#fbbf24" stroke-width="1.5"/>
  <rect x="52" y="38" width="14" height="11" rx="3" fill="#18181b" stroke="#fbbf24" stroke-width="1.5"/>
  <line x1="48" y1="42" x2="52" y2="42" stroke="#fbbf24" stroke-width="2"/>
  <path d="M40 58 Q50 70 60 58 Z" fill="#ffffff" stroke="#451a03" stroke-width="1"/>
  <path d="M20 96 C24 76 38 72 50 72 C62 72 76 76 80 96 Z" fill="#15803d"/>
  <polygon points="44,72 50,86 56,72" fill="#f59e0b"/>
</svg>""",

    "jimi_hendrix": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-hendrix" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#6b21a8"/>
      <stop offset="100%" stop-color="#1e0836"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-hendrix)" stroke="#c084fc" stroke-width="2"/>
  <circle cx="50" cy="40" r="32" fill="#18181b"/>
  <circle cx="28" cy="42" r="14" fill="#18181b"/>
  <circle cx="72" cy="42" r="14" fill="#18181b"/>
  <path d="M26 40 Q50 34 74 40 L73 47 Q50 41 27 47 Z" fill="#ec4899"/>
  <polygon points="24,44 16,54 22,56 26,46" fill="#f43f5e"/>
  <path d="M35 44 Q50 40 65 44 Q67 60 62 70 Q50 78 38 70 Q33 60 35 44 Z" fill="#854d0e"/>
  <path d="M40 50 Q45 48 48 51" stroke="#291807" stroke-width="2" fill="none"/>
  <path d="M60 50 Q55 48 52 51" stroke="#291807" stroke-width="2" fill="none"/>
  <path d="M42 62 Q50 64 58 62 Q54 67 50 65 Q46 67 42 62 Z" fill="#18181b"/>
  <circle cx="50" cy="69" r="1.5" fill="#18181b"/>
  <path d="M20 96 C24 76 38 72 50 72 C62 72 76 76 80 96 Z" fill="#3b0764"/>
  <line x1="36" y1="80" x2="64" y2="80" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="38" y1="88" x2="62" y2="88" stroke="#fbbf24" stroke-width="2.5" stroke-linecap="round"/>
</svg>""",

    "fela_kuti": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-fela" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#ea580c"/>
      <stop offset="100%" stop-color="#431407"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-fela)" stroke="#fb923c" stroke-width="2"/>
  <path d="M34 32 C34 20 44 16 54 16 C64 16 70 20 70 32 Q72 56 64 68 Q54 76 40 68 Q32 56 34 32 Z" fill="#713f12"/>
  <path d="M34 32 C34 20 44 16 54 16 C64 16 70 20 70 32 Q54 26 34 32 Z" fill="#18181b"/>
  <ellipse cx="44" cy="42" rx="3.5" ry="2" fill="#ffffff"/>
  <circle cx="44" cy="42" r="1.8" fill="#18181b"/>
  <ellipse cx="60" cy="42" rx="3.5" ry="2" fill="#ffffff"/>
  <circle cx="60" cy="42" r="1.8" fill="#18181b"/>
  <circle cx="38" cy="48" r="1.5" fill="#ffffff"/>
  <circle cx="42" cy="50" r="1.5" fill="#ffffff"/>
  <circle cx="46" cy="51" r="1.5" fill="#ffffff"/>
  <circle cx="58" cy="51" r="1.5" fill="#ffffff"/>
  <circle cx="62" cy="50" r="1.5" fill="#ffffff"/>
  <circle cx="66" cy="48" r="1.5" fill="#ffffff"/>
  <path d="M52 64 C56 70 56 80 50 86 C44 92 34 88 32 80 L36 80 C37 84 43 87 46 84 C49 80 49 72 46 66 Z" fill="#f59e0b"/>
  <polygon points="30,76 24,72 26,84 34,82" fill="#fbbf24" stroke="#d97706" stroke-width="1"/>
  <path d="M22 96 C24 76 36 72 46 72 L50 84 L54 72 C64 72 76 76 78 96 Z" fill="#eab308"/>
</svg>""",

    "madonna": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-madonna" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#db2777"/>
      <stop offset="100%" stop-color="#3f0723"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-madonna)" stroke="#f472b6" stroke-width="2"/>
  <path d="M22 46 C16 30 24 16 38 14 C48 12 62 12 72 16 C86 22 86 38 80 50 C86 36 82 22 68 18 C56 14 40 16 28 24 C22 30 20 40 22 46 Z" fill="#fef08a"/>
  <path d="M42 16 C34 10 32 6 38 6 C44 6 46 12 48 16 Z" fill="#18181b"/>
  <path d="M58 16 C66 10 68 6 62 6 C56 6 54 12 52 16 Z" fill="#18181b"/>
  <circle cx="50" cy="16" r="3.5" fill="#27272a"/>
  <path d="M36 34 Q50 30 64 34 Q68 54 60 68 Q50 76 40 68 Q32 54 36 34 Z" fill="#fed7aa"/>
  <path d="M40 40 Q45 37 49 40" stroke="#18181b" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <path d="M60 40 Q55 37 51 40" stroke="#18181b" stroke-width="2.5" stroke-linecap="round" fill="none"/>
  <polygon points="41,45 48,45 46,47" fill="#18181b"/>
  <polygon points="59,45 52,45 54,47" fill="#18181b"/>
  <path d="M44 61 Q50 65 56 61 Q50 67 44 61 Z" fill="#e11d48"/>
  <circle cx="43" cy="59" r="1.2" fill="#18181b"/>
  <path d="M24 96 C26 78 38 72 50 72 C62 72 74 78 76 96 Z" fill="#09090b"/>
  <line x1="50" y1="74" x2="50" y2="88" stroke="#e2e8f0" stroke-width="1.8"/>
  <line x1="46" y1="78" x2="54" y2="78" stroke="#e2e8f0" stroke-width="1.8"/>
</svg>""",

    "amy_winehouse": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-amy" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#0d9488"/>
      <stop offset="100%" stop-color="#042f2e"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-amy)" stroke="#2dd4bf" stroke-width="2"/>
  <path d="M30 46 C24 34 26 10 50 8 C74 10 76 34 70 46 C76 36 74 16 50 14 C26 16 24 36 30 46 Z" fill="#09090b"/>
  <ellipse cx="50" cy="24" rx="22" ry="16" fill="#09090b"/>
  <circle cx="32" cy="26" r="6" fill="#ef4444"/>
  <circle cx="30" cy="24" r="2" fill="#fde047"/>
  <path d="M35 40 Q50 36 65 40 Q67 58 61 70 Q50 78 39 70 Q33 58 35 40 Z" fill="#fed7aa"/>
  <polygon points="38,48 49,46 48,48 36,46" fill="#09090b"/>
  <polygon points="62,48 51,46 52,48 64,46" fill="#09090b"/>
  <path d="M44 64 Q50 67 56 64 Q50 69 44 64 Z" fill="#dc2626"/>
  <circle cx="43" cy="59" r="1.2" fill="#09090b"/>
  <ellipse cx="33" cy="54" rx="2" ry="6" fill="none" stroke="#fbbf24" stroke-width="2"/>
  <path d="M22 96 C24 78 38 74 50 74 C62 74 76 78 78 96 Z" fill="#18181b"/>
  <polygon points="42,74 50,86 58,74" fill="#fed7aa"/>
</svg>""",

    "daft_punk": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-daft" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#1f2937"/>
      <stop offset="100%" stop-color="#030712"/>
    </radialGradient>
    <linearGradient id="visor-led" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" stop-color="#ef4444"/>
      <stop offset="25%" stop-color="#f59e0b"/>
      <stop offset="50%" stop-color="#10b981"/>
      <stop offset="75%" stop-color="#06b6d4"/>
      <stop offset="100%" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-daft)" stroke="#fbbf24" stroke-width="2"/>
  <path d="M28 44 C28 24 38 16 50 16 C62 16 72 24 72 44 Q74 62 66 70 Q50 76 34 70 Q26 62 28 44 Z" fill="#fbbf24" stroke="#d97706" stroke-width="2"/>
  <polygon points="34,66 50,74 66,66 62,76 50,80 38,76" fill="#ca8a04"/>
  <circle cx="26" cy="48" r="4.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
  <circle cx="74" cy="48" r="4.5" fill="#e2e8f0" stroke="#64748b" stroke-width="1.5"/>
  <path d="M30 42 Q50 38 70 42 L68 54 Q50 50 32 54 Z" fill="#09090b" stroke="#ca8a04" stroke-width="1"/>
  <path d="M32 44 Q50 40 68 44 L67 52 Q50 48 33 52 Z" fill="url(#visor-led)"/>
  <line x1="33" y1="48" x2="67" y2="48" stroke="#ffffff" stroke-width="1" opacity="0.8"/>
  <path d="M20 96 C24 78 36 74 50 74 C64 74 76 78 80 96 Z" fill="#09090b"/>
  <line x1="50" y1="76" x2="50" y2="96" stroke="#94a3b8" stroke-width="2" stroke-dasharray="3 1"/>
</svg>""",

    "drake": """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">
  <defs>
    <radialGradient id="bg-drake" cx="50%" cy="40%" r="60%">
      <stop offset="0%" stop-color="#713f12"/>
      <stop offset="100%" stop-color="#0a0a0a"/>
    </radialGradient>
  </defs>
  <circle cx="50" cy="50" r="48" fill="url(#bg-drake)" stroke="#eab308" stroke-width="2"/>
  <path d="M32 36 C32 20 42 16 52 16 C62 16 70 20 70 36 Z" fill="#18181b"/>
  <path d="M40 22 C38 19 35 20 35 23 C35 25 39 28 40 29 C41 28 45 25 45 23 C45 20 42 19 40 22 Z" fill="#fde047"/>
  <path d="M34 36 Q52 32 68 36 Q70 56 64 68 Q52 76 38 68 Q32 56 34 36 Z" fill="#9a3412"/>
  <ellipse cx="44" cy="44" rx="3" ry="1.8" fill="#18181b"/>
  <ellipse cx="58" cy="44" rx="3" ry="1.8" fill="#18181b"/>
  <path d="M36 54 C36 70 44 76 52 76 C60 76 66 70 66 54 C66 58 60 62 52 62 C44 62 36 58 36 54 Z" fill="#18181b"/>
  <path d="M44 56 Q52 54 58 56 Q52 59 44 56 Z" fill="#18181b"/>
  <path d="M20 96 C24 76 36 72 52 72 C66 72 78 76 82 96 Z" fill="#1c1917"/>
  <path d="M42 74 Q52 86 60 74" stroke="#fbbf24" stroke-width="3" fill="none" stroke-linecap="round"/>
  <circle cx="51" cy="85" r="4" fill="#fbbf24"/>
  <circle cx="49.5" cy="84" r="1.2" fill="#1c1917"/>
  <circle cx="52.5" cy="84" r="1.2" fill="#1c1917"/>
</svg>"""
}
