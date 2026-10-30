"""
Drop-in Custom Plugin Module for Vana'diel Nexus (modules/sortie_helper.py).
Any .py file placed in modules/ exposing MODULE_METADATA is auto-loaded!
"""

MODULE_METADATA = {
    "id": "mod-sortie-helper",
    "name": "Sortie & Odyssey Daily Checklist Module",
    "category": "Custom Plugin (modules/)",
    "loaded": True,
    "autoJob": "All Jobs",
    "desc": "Tracks daily Sortie Sector A-H objectives, Old Case +1/+2 counts, and Odyssey Mogolophone timers.",
}

def on_action(send_udp_func):
    send_udp_func("SCAN")
    return "Triggered Sortie/Odyssey inventory & currency refresh via UDP!"
