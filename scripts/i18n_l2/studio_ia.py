"""t185 (G3, plan « Génération IA enrichie ») — le nœud Seedance du Studio et son port `end` (image de fin) : le
sélecteur de modèle (DzVideoModelSel, maillon de queue patch_bundle_encartsia) dit quand le modèle choisi ne prend
pas d'image de fin et propose Veo 3.1 Fast en un clic ; il rappelle l'image de fin branchée. Entrées D : le texte
vit dans le code du maillon, pas dans le bundle de base."""
from outils import D

ENTREES = [
    D('studio.video.fl', 'Veo 3.1 Fast (début et fin)', 'Veo 3.1 Fast (first and last frame)'),
    D('studio.video.fl_absent', "Ce modèle ne prend pas d'image de fin : le lancement serait refusé.",
      'This model takes no last frame: the launch would be refused.'),
    D('studio.compose.fin', 'Image de fin du créneau', 'Slot last frame'),
]
