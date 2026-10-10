# Documents de démonstration du Vectorlab (t177) sur le backend de PREUVE : une affiche vectorielle en trois
# calques (fond, phare, titre) et une planche de tuiles. Dessinés ici, gratuits, aucune clé. Jamais le 8765.
import json
import sys
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8809"
assert ":8765" not in BASE


def poster(nom, doc):
    req = urllib.request.Request(BASE + "/api/vector/docs", method="POST",
                                 data=json.dumps({"name": nom, "role": "libre", "doc": doc}).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["id"]


def st(fond, contour=None, ep=0):
    s = {"fond": fond}
    if contour:
        s.update(contour=contour, epaisseur=ep)
    return s


affiche = {
    "v": 1, "nom": "Affiche du phare", "taille": {"w": 1080, "h": 1350},
    "calques": [
        {"id": "c1", "nom": "Fond", "visible": True, "verrou": False, "objets": [
            {"id": "ciel", "type": "rect", "x": 0, "y": 0, "w": 1080, "h": 950, "style": st("#1F2A52")},
            {"id": "soleil", "type": "ellipse", "cx": 760, "cy": 640, "rx": 150, "ry": 150, "style": st("#F5C451")},
            {"id": "mer", "type": "rect", "x": 0, "y": 950, "w": 1080, "h": 400, "style": st("#12405E")},
            {"id": "vague", "type": "path", "d": "M0 1010 C 180 960 360 1060 540 1010 S 900 960 1080 1010",
             "style": {"fond": "none", "contour": "#7FB8D6", "epaisseur": 10}},
        ]},
        {"id": "c2", "nom": "Phare", "visible": True, "verrou": False, "objets": [
            {"id": "tour", "type": "path", "d": "M330 950 L400 420 L500 420 L570 950 Z", "style": st("#F1EEE6", "#1F1512", 4)},
            {"id": "bande1", "type": "rect", "x": 372, "y": 560, "w": 156, "h": 50, "style": st("#C8323C")},
            {"id": "bande2", "type": "rect", "x": 352, "y": 730, "w": 196, "h": 50, "style": st("#C8323C")},
            {"id": "lanterne", "type": "rect", "x": 405, "y": 350, "w": 90, "h": 70, "rx": 8, "style": st("#FFE08A", "#1F1512", 4)},
            {"id": "toit", "type": "path", "d": "M385 352 L450 290 L515 352 Z", "style": st("#2B2B35")},
        ]},
        {"id": "c3", "nom": "Titre", "visible": True, "verrou": False, "objets": [
            {"id": "titre", "type": "texte", "x": 540, "y": 1210, "contenu": "LE PHARE DU RÉCIF",
             "style": {"fond": "#F5C451", "corps": 84, "graisse": 800, "ancre": "middle"}},
        ]},
    ],
}

tuiles = {
    "v": 1, "nom": "Planche de tuiles", "taille": {"w": 1024, "h": 1024},
    "calques": [{"id": "c1", "nom": "Tuiles", "visible": True, "verrou": False, "objets": [
        {"id": f"t{i}{j}", "type": "rect", "x": 64 + i * 224, "y": 64 + j * 224, "w": 200, "h": 200, "rx": 12,
         "style": st(["#5DA36B", "#C9A86B", "#4F7FB3", "#8C8C99"][(i + j) % 4])}
        for i in range(4) for j in range(4)]}],
}

print("affiche :", poster("Affiche du phare", affiche))
print("tuiles :", poster("Planche de tuiles", tuiles))
