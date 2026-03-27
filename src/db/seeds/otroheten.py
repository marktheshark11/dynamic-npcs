"""
Seed: Otrohetsmysteriet
=======================
Lagger in hela delmysteriet "Otroheten" i databasen.

Kor med:  python -m db.seeds.otroheten
"""

from db.config import Config
from db.services import EmbeddingService
from db.repositories import (
    NPCRepo, ClaimRepo, ConstantRepo, OpinionRepo, RelationRepo, MysteryRepo,
)
from db.models import NPC


# ============================================================================
# DATA
# ============================================================================

NPCS = [
    NPC(
        id="npc_nils",
        name="Lord Nils Wolmarsson",
        age=85,
        personality="Stolt, kontrollerande, misstänksam, hård men intelligent.",
        status="Levande",
        story_background=(
            "Patriarken på Wolmars Slott. Har byggt sin identitet på familj, "
            "arv och tradition. Efter Silvias död gifte han om sig med Pamela. "
            "Börjar misstänka att han blivit utnyttjad och förrådd."
        ),
    ),
    NPC(
        id="npc_pamela",
        name="Pamela Smith Wolmarsson",
        age=38,
        personality="Charmig, socialt skicklig, manipulativ, lätt defensiv under press.",
        status="Levande",
        story_background=(
            "Gift med Nils för status och ekonomisk trygghet. Van vid att spela "
            "olika roller beroende på vem hon pratar med. Har en hemlig affär "
            "med advokaten Bergström."
        ),
    ),
    NPC(
        id="npc_bergstrom",
        name="Herr Bergström",
        age=45,
        personality="Professionell, kontrollerad, smart, beräknande. Kan bli kall när han känner sig hotad.",
        status="Levande",
        story_background=(
            "Familjens advokat. Har byggt sitt rykte på diskretion och "
            "trovärdighet. Har en affär med Pamela och riskerar både karriär "
            "och frihet om det avslöjas."
        ),
    ),
    NPC(
         id="npc_mariana",
         name="Mariana Martinsson",
         age=72,
        personality="Moderlig, observant, lojal, passivt aggressiv, hämndlysten mot hot.",
        status="Levande",
        story_background=(
            "Hushållerska på slottet i många år. Har sett barnen växa upp och "
            "ser sig som en del av familjen. Hon avskyr Pamela eftersom hon "
            "upplever henne som falsk och hotande. Mariana är villig att "
            "manipulera situationer för att skydda \"familjen\"."
        ),
    ),
    NPC(
        id="npc_beatrice",
        name="Beatrice Wolmarsson",
        age=30,
        personality="Känslostyrd men kontrollerad utåt, stolt, lätt paranoid, svartsjuk på Pamela.",
        status="Levande",
        story_background=(
            "Uppvuxen på slottet och ser det som sitt hem. Har svårt att "
            "acceptera Pamela som ny fru. Beatrice observerar stämningar och "
            "sociala signaler, särskilt kring Pamela."
        ),
    ),
    NPC(
        id="npc_wilhelm",
        name="Wilhelm Wolmarsson",
        age=33,
        personality="Släpig, cynisk, känslig, rebellisk, oberäknelig.",
        status="Levande",
        story_background=(
            "Sonen i familjen. Har missbruksproblem och en komplicerad relation "
            "till sin far. Misstänker ofta att folk ljuger. Bra som "
            "\"semi-opålitlig observatör\" som ser saker men tolkar fel."
        ),
    ),
]

# Shorthand names → full NPC names (for REFERENCE targets)
N = {
     "Pamela":     "Pamela Smith Wolmarsson",
     "Bergström":  "Herr Bergström",
     "Mariana":    "Mariana Martinsson",
     "Nils":       "Lord Nils Wolmarsson",
     "Beatrice":   "Beatrice Wolmarsson",
     "Wilhelm":    "Wilhelm Wolmarsson",
}

OBJECTS = ["Parfym", "Brev", "Lapp", "Båt", "Testamente", "Rivmärken", "Middag"]

PLACES = [
    "Wolmars Slott",
    "Bryggan",
    "Skogen",
    "Matsalen",
    "Pamelas rum",
    "Marianas rum",
    "Eldstad",
]

# Claims: (key, content, type_or_none)
CLAIMS = [
    # --- KARNCLAIMS (relationen) ---
    ("O1",  "Pamela och Herr Bergström har en affär.", "relation"),
    ("O2",  "Pamela är lojal mot Nils och skulle aldrig vara otrogen.", "relation"),
    ("O3",  "Herr Bergström skulle aldrig riskera sin karriär genom att vara intim med sin klients fru.", "relation"),

    # --- COVER STORY / ALIBI ---
    ("O4",  "Pamela gick och la sig tidigt och var i sitt rum resten av natten.", None),
    ("O5",  "Efter mötet med Nils lämnade Bergström ön direkt.", None),
    ("O6",  "Pamela och Bergström träffades inte efter middagen.", None),

    # --- MARIANAS OBSERVATIONER ---
    ("O7",  "Mariana såg Pamela och Bergström tillsammans utomhus genom sitt fönster sent på kvällen.", None),
    ("O8",  "Mariana såg att Bergströms båt låg kvar sent på kvällen.", None),

    # --- SOCIALA SIGNALER ---
    ("O9",  "Under middagen tittade Pamela och Bergström ofta på varandra.", None),
    ("O10", "Under middagen hade Pamela och Bergström en ovanligt intim ton.", None),
    ("O11", "Beatrice märkte att Pamela blev spänd när Bergström nämndes.", None),
    ("O12", "Wilhelm märkte att Bergström undvek att prata om vad mötet med Nils handlade om.", None),

    # --- FYSISKA INDICIER ---
    ("O13", "Bergströms kläder luktade parfym morgonen efter.", None),
    ("O14", "Pamela hade jord och barr på sina skor morgonen efter.", None),
    ("O15", "Bergström hade rivmärken på armen morgonen efter.", None),
    ("O16", "Pamela hade färska märken på händerna som om hon varit ute i terräng.", None),

    # --- KOMMUNIKATION / HEMLIGA SPAR ---
    ("O17", "Pamela och Bergström har haft privat kontakt innan resan till slottet.", None),
    ("O18", "Pamela försökte göra sig av med ett brev sent på kvällen.", None),
    ("O19", "Bergström bar på ett föremål eller en lapp kopplad till Pamela.", None),

    # --- EKONOMI / KONSPIRATION ---
    ("O20", "Pamela har försökt påverka Nils att ändra testamentet.", None),
    ("O21", "Bergström skulle gynnas ekonomiskt om testamentet ändras.", None),
    ("O22", "Pamela och Bergström diskuterade Nils arv i hemlighet.", None),

    # --- MARIANAS MOTIV ---
    ("O23", "Mariana hatar Pamela och vill få bort henne från slottet.", "relation"),
    ("O24", "Mariana samlar aktivt information som kan användas mot Pamela.", None),
]

# REFERENCE: key → list of (target_name, target_type)
# NPC names use the N[] shorthand, which maps to full names
# OBJECT/PLACE names use the capitalized form (as stored by repos)
REFERENCES: dict[str, list[tuple[str, str]]] = {
    "O1":  [(N["Pamela"], "NPC"), (N["Bergström"], "NPC")],
    "O2":  [(N["Pamela"], "NPC"), (N["Nils"], "NPC")],
    "O3":  [(N["Bergström"], "NPC"), (N["Pamela"], "NPC"), (N["Nils"], "NPC")],
    "O4":  [(N["Pamela"], "NPC"), ("Pamelas rum", "PLACE")],
    "O5":  [(N["Bergström"], "NPC"), ("Bryggan", "PLACE"), ("Båt", "OBJECT")],
    "O6":  [(N["Pamela"], "NPC"), (N["Bergström"], "NPC")],
    "O7":  [(N["Mariana"], "NPC"), (N["Pamela"], "NPC"), (N["Bergström"], "NPC"),
            ("Marianas rum", "PLACE"), ("Wolmars slott", "PLACE")],
    "O8":  [(N["Mariana"], "NPC"), (N["Bergström"], "NPC"),
            ("Båt", "OBJECT"), ("Bryggan", "PLACE")],
    "O9":  [(N["Pamela"], "NPC"), (N["Bergström"], "NPC"), ("Middag", "OBJECT")],
    "O10": [(N["Pamela"], "NPC"), (N["Bergström"], "NPC"), ("Middag", "OBJECT")],
    "O11": [(N["Beatrice"], "NPC"), (N["Pamela"], "NPC"), (N["Bergström"], "NPC")],
    "O12": [(N["Wilhelm"], "NPC"), (N["Bergström"], "NPC"), (N["Nils"], "NPC")],
    "O13": [(N["Bergström"], "NPC"), ("Parfym", "OBJECT")],
    "O14": [(N["Pamela"], "NPC")],
    "O15": [(N["Bergström"], "NPC")],
    "O16": [(N["Pamela"], "NPC")],
    "O17": [(N["Pamela"], "NPC"), (N["Bergström"], "NPC")],
    "O18": [(N["Pamela"], "NPC"), ("Brev", "OBJECT"), ("Eldstad", "PLACE")],
    "O19": [(N["Bergström"], "NPC"), (N["Pamela"], "NPC"), ("Lapp", "OBJECT")],
    "O20": [(N["Pamela"], "NPC"), (N["Nils"], "NPC"), ("Testamente", "OBJECT")],
    "O21": [(N["Bergström"], "NPC"), ("Testamente", "OBJECT")],
    "O22": [(N["Pamela"], "NPC"), (N["Bergström"], "NPC"),
            (N["Nils"], "NPC"), ("Testamente", "OBJECT")],
    "O23": [(N["Mariana"], "NPC"), (N["Pamela"], "NPC")],
    "O24": [(N["Mariana"], "NPC"), (N["Pamela"], "NPC")],
}

# HAS_OPINION: (npc_id, claim_key, belief_in, openness)
OPINIONS = [
    # --- Pamela ---
    ("npc_pamela", "O1",  +1.0, -0.9),
    ("npc_pamela", "O2",  +0.9, +0.9),
    ("npc_pamela", "O4",  +0.9, +0.8),
    ("npc_pamela", "O6",  +0.9, +0.9),
    ("npc_pamela", "O14", +1.0, -0.4),
    ("npc_pamela", "O18", +1.0, -0.8),

    # --- Bergström ---
    ("npc_bergstrom", "O1",  +1.0, -0.8),
    ("npc_bergstrom", "O3",  +0.8, +0.6),
    ("npc_bergstrom", "O5",  +0.9, +0.8),
    ("npc_bergstrom", "O6",  +0.8, +0.7),
    ("npc_bergstrom", "O13", +1.0, -0.3),
    ("npc_bergstrom", "O15", +1.0, -0.6),

    # --- Mariana ---
    ("npc_mariana", "O1",  +0.9, +0.5),
    ("npc_mariana", "O7",  +1.0, -0.2),
    ("npc_mariana", "O8",  +1.0, +0.6),
    ("npc_mariana", "O23", +1.0, -0.6),
    ("npc_mariana", "O24", +1.0, -0.8),

    # --- Beatrice ---
    ("npc_beatrice", "O9",  +0.6, +0.4),
    ("npc_beatrice", "O10", +0.7, +0.3),
    ("npc_beatrice", "O11", +1.0, +0.6),
    ("npc_beatrice", "O2",  -0.4, +0.7),
    ("npc_beatrice", "O1",  +0.5, +0.3),

    # --- Wilhelm ---
    ("npc_wilhelm", "O12", +0.8, +0.6),
    ("npc_wilhelm", "O1",  +0.4, +0.8),
    ("npc_wilhelm", "O3",  -0.6, +0.7),

    # --- Nils ---
    ("npc_nils", "O2",  -0.2, -0.5),
    ("npc_nils", "O1",  +0.4, -0.8),
    ("npc_nils", "O20", +0.8, -0.2),
]


# ============================================================================
# SEED LOGIC
# ============================================================================

def seed() -> None:
    config = Config.from_env()

    try:
        embedding = EmbeddingService(config.embed_model)
        npc_repo = NPCRepo(config.driver)
        claim_repo = ClaimRepo(config.driver, embedding)
        constant_repo = ConstantRepo(config.driver)
        opinion_repo = OpinionRepo(config.driver)
        relation_repo = RelationRepo(config.driver)
        mystery_repo = MysteryRepo(config.driver)

        # 1. NPCs
        print("=== NPCs ===")
        for npc in NPCS:
            npc_repo.create(npc)
            print(f"  + {npc.id}: {npc.name}")

        # 2. Objects
        print("\n=== OBJECTS ===")
        for name in OBJECTS:
            obj = constant_repo.create_object(name)
            print(f"  + OBJECT: {obj.name}")

        # 3. Places
        print("\n=== PLACES ===")
        for name in PLACES:
            place = constant_repo.create_place(name)
            print(f"  + PLACE: {place.name}")

        # 4. Mystery
        print("\n=== MYSTERY ===")
        mystery = mystery_repo.create("Otroheten")
        print(f"  + MYSTERY: {mystery.name}")

        # 5. Claims (embeddings tar tid)
        print(f"\n=== CLAIMS ({len(CLAIMS)} st, genererar embeddings...) ===")
        # Map O-keys to real claim IDs
        claim_ids: dict[str, str] = {}
        for i, (key, content, claim_type) in enumerate(CLAIMS, 1):
            claim = claim_repo.create(content, claim_type=claim_type)
            claim_ids[key] = claim.claim_id
            tag = f" [{claim_type}]" if claim_type else ""
            print(f"  [{i}/{len(CLAIMS)}] {key} -> {claim.claim_id}{tag}: {content[:60]}")

        # 6. PART_OF (claims -> mystery)
        print(f"\n=== PART_OF ===")
        for key, cid in claim_ids.items():
            mystery_repo.link_claim(cid, mystery.name)
        print(f"  + {len(claim_ids)} claims kopplade till '{mystery.name}'")

        # 7. REFERENCE
        print(f"\n=== REFERENCE ===")
        ref_count = 0
        for key, refs in REFERENCES.items():
            cid = claim_ids[key]
            for target_name, target_type in refs:
                ok = relation_repo.create_reference(cid, target_name, target_type)
                if ok:
                    ref_count += 1
                else:
                    print(f"  ! MISSLYCKAD: {cid} -> [{target_type}] {target_name}")
        print(f"  + {ref_count} REFERENCE-relationer skapade")

        # 8. HAS_OPINION
        print(f"\n=== HAS_OPINION ===")
        opinion_count = 0
        for npc_id, claim_key, belief_in, openness in OPINIONS:
            cid = claim_ids[claim_key]
            ok = opinion_repo.create(npc_id, "NPC", cid, belief_in, openness)
            if ok:
                opinion_count += 1
            else:
                print(f"  ! MISSLYCKAD: {npc_id} -> {cid} ({claim_key})")
        print(f"  + {opinion_count} HAS_OPINION-relationer skapade")

        # Summary
        print("\n" + "=" * 50)
        print("SAMMANFATTNING")
        print("=" * 50)
        print(f"  NPCs:          {len(NPCS)}")
        print(f"  Objects:       {len(OBJECTS)}")
        print(f"  Places:        {len(PLACES)}")
        print(f"  Mystery:       {mystery.name}")
        print(f"  Claims:        {len(CLAIMS)}")
        print(f"  PART_OF:       {len(claim_ids)}")
        print(f"  REFERENCE:     {ref_count}")
        print(f"  HAS_OPINION:   {opinion_count}")
        print(f"\nClaim-ID-mappning:")
        for key, cid in claim_ids.items():
            print(f"  {key} -> {cid}")

    finally:
        config.close()


if __name__ == "__main__":
    seed()
