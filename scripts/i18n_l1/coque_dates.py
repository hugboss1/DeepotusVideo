"""t141 — les dates relatives de la coque : mo(), utilisée par les cartes de la Bibliothèque, la file des rendus et
d'autres vues (8 appels). La date absolue suit la langue affichée (dzLang()) au lieu d'un « en » figé."""
from outils import S

ENTREES = [
    S(156241,
      '`${Math.round(n)}s ago`:n<3600?`${Math.round(n/60)}m ago`:n<86400?`${Math.round(n/3600)}h ago`:'
      'n<86400*7?`${Math.round(n/86400)}d ago`:new Date(e).toLocaleString("en",',
      'dzT("coque.date.secondes",{n:Math.round(n)}):n<3600?dzT("coque.date.minutes",{n:Math.round(n/60)}):'
      'n<86400?dzT("coque.date.heures",{n:Math.round(n/3600)}):n<86400*7?dzT("coque.date.jours",{n:Math.round(n/86400)}):'
      'new Date(e).toLocaleString(dzLang(),',
      {"coque.date.secondes": ("il y a {n} s", "{n}s ago"),
       "coque.date.minutes": ("il y a {n} min", "{n}m ago"),
       "coque.date.heures": ("il y a {n} h", "{n}h ago"),
       "coque.date.jours": ("il y a {n} j", "{n}d ago")}),
]
