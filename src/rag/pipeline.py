from db.repositories import NPCRepo, PlayerRepo, RAGRepo
from prompt_builder import NPCProfile, PromptBuilder, PromptRequest, RAGContext
from rag.rendering import Rendering
import sys


class RAGPipeline:
    def __init__(self, driver, embed_model):
        self.rag_repo = RAGRepo(driver)
        self.npc_repo = NPCRepo(driver)
        self.player_repo = PlayerRepo(driver)
        self.embed_model = embed_model
        self.prompt_builder = PromptBuilder()
        self._group_support: bool | None = None
        self.up_steps: int = 3

    def _supports_group_membership(self) -> bool:
        if self._group_support is not None:
            return self._group_support
        self._group_support = self.rag_repo.supports_group_membership()
        return self._group_support

    def _create_query_embedding(self, text: str) -> list[float]:
        return self.embed_model.embed_query(f"Represent this sentence for searching relevant passages: {text}")

    def _rewrite_query(
        self,
        question: str,
        recent_exchanges: list[dict] | None,
        story_background: str | None = None,
        mentioned_claims: list[dict] | None = None,
    ) -> str:
        """Skriver om spelarens fråga till en informationsrik sökfras för RAG.
        Använder berättelsebakgrund, nämnda fakta och konversationshistorik för att
        lösa upp pronomen och skapa en semantiskt rikare sökfras."""
        from llms.llm_groq import chat as groq_chat

        history_lines = []
        for ex in (recent_exchanges or []):
            player_text = ex.get("player_text") or ""
            npc_text = ex.get("npc_text") or ""
            if player_text:
                history_lines.append(f"Spelare: {player_text}")
            if npc_text:
                history_lines.append(f"NPC: {npc_text}")
        history_block = "\n".join(history_lines) if history_lines else "(ingen historik)"

        mentioned_lines = [c["content"] for c in (mentioned_claims or []) if c.get("content")]
        mentioned_block = "\n".join(f"- {m}" for m in mentioned_lines) if mentioned_lines else "(inga)"

        background_block = story_background.strip() if story_background else "(ingen bakgrund)"

        messages = [
            {
                "role": "system",
                "content": (
                    "Du är ett verktyg för frågeomskrivning för RAG (Retrieval-Augmented Generation).\n"
                    "Din uppgift är att ta spelarens fråga och skriva om den till en informationsrik "
                    "sökfras optimerad för vektordatabassökning.\n"
                    "Du har tillgång till berättelsens bakgrund, tidigare nämnd information och konversationshistorik.\n"
                    "Regler:\n"
                    "- Ersätt alla pronomen (han, hon, det, där, etc.) med konkreta namn och platser från kontexten.\n"
                    "- Inkludera relevant kontext som hjälper sökningen.\n"
                    "- Skriv på svenska.\n"
                    "- Returnera BARA sökfrasen som ren text, utan förklaring eller kommentarer."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"BERÄTTELSEBAKGRUND:\n{background_block}\n\n"
                    f"TIDIGARE NÄMNDA FAKTA:\n{mentioned_block}\n\n"
                    f"KONVERSATIONSHISTORIK:\n{history_block}\n\n"
                    f"SPELARENS FRÅGA: {question}\n\n"
                    "SÖKFRAS:"
                ),
            },
        ]

        rewritten = groq_chat(messages=messages, max_tokens=128).strip()
        if rewritten and rewritten != question:
            print(f"[Sökfras: {rewritten}]", file=sys.stderr)
        return rewritten if rewritten else question

    def _get_reference_chain(self, claim_id: str, npc_id: str) -> list[dict]:
        include_group = self._supports_group_membership()
        down = self.rag_repo.get_reference_chain(
            claim_id=claim_id,
            npc_id=npc_id,
            include_group=include_group,
        )
        up = (
            self.rag_repo.get_upstream_claims(
                claim_id=claim_id,
                npc_id=npc_id,
                up_steps=self.up_steps,
                include_group=include_group,
            )
            if self.up_steps > 0
            else []
        )
        combined = up + down
        seen: set[str] = set()
        unique: list[dict] = []
        for c in sorted(combined, key=lambda x: x["depth"]):
            if c["id"] not in seen:
                seen.add(c["id"])
                unique.append(c)
        return unique

    def _build_claim_chains(self, claims: list[dict], npc_id: str, already_mentioned: set[str] | None = None) -> list[dict]:
        if not claims:
            return []

        all_nodes = {}
        adj = {}
        potential_roots = set()

        for claim in claims:
            chain = self._get_reference_chain(claim["id"], npc_id)
            if not chain:
                continue

            for chain_claim in chain:
                all_nodes[chain_claim["id"]] = chain_claim
                if chain_claim["id"] not in adj:
                    adj[chain_claim["id"]] = []
                potential_roots.add(chain_claim["id"])

            for index in range(len(chain) - 1, 0, -1):
                parent = chain[index]
                child = chain[index - 1]
                if child["id"] not in adj[parent["id"]]:
                    adj[parent["id"]].append(child["id"])
                if child["id"] in potential_roots:
                    potential_roots.remove(child["id"])

        final_chains = []
        visited = set()

        def dfs(node_id: str) -> list[dict]:
            if node_id in visited:
                return []
            visited.add(node_id)
            result = [all_nodes[node_id]]
            for child_id in adj.get(node_id, []):
                result.extend(dfs(child_id))
            return result

        for root_id in list(potential_roots):
            if root_id in visited:
                continue

            chain_nodes = dfs(root_id)
            if not chain_nodes:
                continue

            contents = [
                Rendering.render_claim_static(
                    chain_claim.get("claim_id"),
                    chain_claim["content"],
                    prefix=chain_claim.get("prefix"),
                    suffix=(
                        (chain_claim.get("overwrite_suffix") or "och detta har du redan nämnt")
                        if already_mentioned and chain_claim.get("claim_id") in already_mentioned
                        else chain_claim.get("suffix")
                    ),
                )
                for chain_claim in chain_nodes
            ]
            ids = [chain_claim["id"] for chain_claim in chain_nodes]

            final_chains.append(
                {
                    "content": " ".join(contents),
                    "ids": ids,
                    "chain_length": len(chain_nodes),
                    "has_relation_type": any(chain_claim.get("type") == "relation" for chain_claim in chain_nodes),
                }
            )

        return final_chains

    def run(
        self,
        npc_id,
        question,
        top_k=3,
        player_profile=None,
        recent_exchanges=None,
        player_id=None,
        conversation_claim_ids=None,
    ):
        # 0. Hämta NPC-profil och nämnda claims tidigt — används av query rewritern
        npc_data = self.npc_repo.get_profile_by_id(npc_id)
        if not npc_data:
            raise ValueError(f"NPC with ID '{npc_id}' not found.")

        remembered_claim_hits = self.rag_repo.find_claims_by_claim_ids(
            npc_id=npc_id,
            claim_ids=conversation_claim_ids or [],
        )

        # 1. Grundsökning (Semantisk) — frågan skrivs om för bättre RAG-träffar
        search_query = self._rewrite_query(
            question,
            recent_exchanges,
            story_background=npc_data.get("story_background"),
            mentioned_claims=remembered_claim_hits,
        )
        query_embedding = self._create_query_embedding(search_query)
        top_claims = self.rag_repo.find_top_claims(npc_id=npc_id, query_vector=query_embedding, top_k=top_k)

        # 1b. Slå ihop semantiska träffar med claims från konversationshistoriken
        combined_hits = top_claims + remembered_claim_hits

        # 2. Expandera för att hitta konstanter (PLACE, OBJECT, NPC, MYSTERY)
        initial_ids = [c["id"] for c in combined_hits]
        all_expanded_claims, constants = self.rag_repo.expand_from_claims(initial_ids)
        constant_ids = [c["id"] for c in constants if c["id"]]

        # 2b. Inkludera alla NPC-claims som delar mystery med de expanderade claimsen
        mystery_ids = [c["id"] for c in constants if c.get("type") == "MYSTERY"]
        mystery_claims = self.rag_repo.find_mystery_claims(mystery_ids, npc_id) if mystery_ids else []

        # 3. Hitta alla "kandidater" för relationer utifrån dina 4 kriterier:
        rel_candidates = self.rag_repo.find_relational_candidates(npc_id=npc_id, constant_ids=constant_ids)

        # 4. Slå ihop allt och bygg kedjor (Logisk pussling)
        all_unique = {
            c["id"]: c
            for c in (combined_hits + all_expanded_claims + mystery_claims + rel_candidates)
        }
        already_mentioned = (
            self.player_repo.get_aware_claim_ids_from_npc(player_id, npc_id)
            if player_id else set()
        )
        chains = self._build_claim_chains(list(all_unique.values()), npc_id, already_mentioned=already_mentioned)
        
        # 5. Sortera: Kedjor > 1 eller fakta -> knowledge. Enstaka relationer -> relation_claims.
        knowledge_final = []
        relation_final = []
        
        for chain in chains:
            # REGEL 1: Serier (längd > 1) går ALLTID till knowledge för kontext
            if chain["chain_length"] > 1:
                knowledge_final.append(chain["content"])
            else:
                # REGEL 2: Endast fristående claims där typen är exakt "relation" 
                # går till relation_claims. Allt annat hamnar i knowledge.
                if chain.get("has_relation_type") == True:
                    relation_final.append(chain["content"])
                else:
                    knowledge_final.append(chain["content"])

        # 6. Paketera för LLM-prompten
        context = RAGContext(
            knowledge_claims=knowledge_final,
            relation_claims=relation_final,
            metadata=constants
        )
        
        profile = NPCProfile(
            name=npc_data["name"],
            personality=npc_data.get("personality", ""),
            backstory=npc_data.get("backstory", ""),
            story_background=npc_data.get("story_background", "")
        )

        request = PromptRequest(
            question=question,
            player_name=(player_profile or {}).get("name"),
            player_appearance=(player_profile or {}).get("appearance"),
            recent_exchanges=recent_exchanges or [],
        )

        prompt_result = self.prompt_builder.build(
            profile=profile,
            rag_context=context,
            request=request
        )

        return prompt_result, chains
