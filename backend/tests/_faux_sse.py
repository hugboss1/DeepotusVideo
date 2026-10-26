# -*- coding: utf-8 -*-
"""L4.1 T3 : le FAUX serveur Anthropic des bancs de l'agent. Depuis que `moteurs_texte.converser` lit le flux SSE
(`stream: true`), la couture `_POSTER` rend une réponse qui a `status_code`, `text` et `iter_lines()`.
`lignes_depuis_message` écrit à la main le flux d'un message complet {content, stop_reason, usage} tel que les bancs
d'avant le rendaient en JSON : un bloc texte = un `text_delta`, un `tool_use` = un `input_json_delta`.
Aucun réseau, aucune dépense."""
import json


def evt(nom, data):
    return [f"event: {nom}", "data: " + json.dumps(data, ensure_ascii=False), ""]


def lignes_depuis_message(d, id_msg="msg_banc"):
    u = d.get("usage") or {}
    L = evt("message_start", {"type": "message_start", "message": {
        "id": id_msg, "type": "message", "role": "assistant", "content": [], "stop_reason": None,
        "usage": {"input_tokens": int(u.get("input_tokens") or 0), "output_tokens": 1}}})
    L += evt("ping", {"type": "ping"})
    for i, b in enumerate(d.get("content") or []):
        if b.get("type") == "text":
            L += evt("content_block_start", {"type": "content_block_start", "index": i,
                                              "content_block": {"type": "text", "text": ""}})
            L += evt("content_block_delta", {"type": "content_block_delta", "index": i,
                                              "delta": {"type": "text_delta", "text": b.get("text") or ""}})
        else:
            L += evt("content_block_start", {"type": "content_block_start", "index": i, "content_block": {
                "type": "tool_use", "id": b.get("id"), "name": b.get("name"), "input": {}}})
            L += evt("content_block_delta", {"type": "content_block_delta", "index": i, "delta": {
                "type": "input_json_delta", "partial_json": json.dumps(b.get("input") or {}, ensure_ascii=False)}})
        L += evt("content_block_stop", {"type": "content_block_stop", "index": i})
    L += evt("message_delta", {"type": "message_delta", "delta": {"stop_reason": d.get("stop_reason"),
                                                                    "stop_sequence": None},
                                "usage": {"output_tokens": int(u.get("output_tokens") or 0)}})
    L += evt("message_stop", {"type": "message_stop"})
    return L


class FluxRep:
    """La réponse simulée : 200 + flux de lignes, ou un statut d'erreur + corps texte."""
    def __init__(self, lignes=None, status_code=200, text=""):
        self.status_code, self._lignes, self.text = status_code, list(lignes or []), text
        self.ferme = False

    def iter_lines(self):
        yield from self._lignes

    def read(self):
        return b""

    def close(self):
        self.ferme = True
