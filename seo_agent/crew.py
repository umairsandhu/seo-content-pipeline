"""Multi-agent crew — a pipeline of expert roles that hand off to take a goal from
idea to shipped, the way a real content+SEO team does. Each stage is grounded by the
deterministic tooling (SERP, corpus, internal links, schema, safety gate) and driven
by the matching expert persona.

Agent-native: `plan()` assembles the staged brief; the driving agent executes each
stage *as* that persona (or a headless LLM does, per stage, when `llm.provider` is
set). The final publish/change stage is gated by BOTH the safety gate and the
autonomy mode. Site-agnostic.

  crew article "<keyword>"    → research → strategy → write → edit → tech-SEO → publish
  crew change  "<goal>"       → diagnose → plan change → tech review → apply (gated)
"""
from . import personas, produce, safetygate, schema
from . import autonomy


def _stage(role, goal, inputs, deliverable):
    return {"role": role, "persona": personas.system(role), "goal": goal,
            "inputs": inputs, "deliverable": deliverable}


def article(cfg, keyword):
    b = produce.brief(cfg, keyword)
    links = produce._link_targets(cfg, keyword, "corpus.json")
    stages = [
        _stage("researcher", f'Assemble the truth set for "{keyword}"',
               {"top_results": b["serp"][:8], "questions": b["questions"][:12], "related": b["related"][:10]},
               "A fact sheet: what the top results cover, the PAA questions, the unique angle/gap, and 3–5 "
               "verifiable data points (with sources) the article should own."),
        _stage("strategist", "Define the winning angle + outline",
               {"keyword": keyword, "internal_link_targets": links},
               "Search intent, the one job this page must do, the differentiated angle, and an H2/H3 outline "
               "that beats the current top results and maps to the PAA questions."),
        _stage("writer", "Write the draft",
               {"outline_from": "strategist", "brand": cfg.get("brand", {}).get("name", "")},
               "The full article in Markdown: SEO title (`# …`), meta (`> meta: …`), answer-first intro, "
               "question H2/H3s, quotable 40–170-word passages, concrete facts, natural internal links."),
        _stage("editor", "Tighten and fact-check",
               {"draft_from": "writer"},
               "A tightened draft: fluff cut, claims verified, intent satisfied better than the top results, "
               "E-E-A-T and answer-first enforced. Note any weak passage rewritten."),
        _stage("tech_seo", "On-page + structured data + linking",
               {"schema_scaffold": schema.blogposting(cfg, {"url": cfg.get("site", ""), "title": keyword,
                                                             "h1": [keyword]}),
                "internal_link_targets": links},
               "Final title/meta (lengths verified), valid BlogPosting/FAQ JSON-LD, internal links added, "
               "and a passage-citability check — ready to publish."),
    ]
    return {"goal": f'article: "{keyword}"', "kind": "article", "stages": stages,
            "publish_gate": "safety gate + autonomy (" + autonomy.mode(cfg) + ")"}


def change(cfg, goal):
    stages = [
        _stage("tech_seo", f"Diagnose: {goal}",
               {"site": cfg.get("site", "")},
               "Root-cause diagnosis and the exact change(s) needed, ordered crawl/index → content → links, "
               "each tied to a crawler/ranking mechanism and a rollback."),
        _stage("strategist", "Justify + prioritize",
               {}, "Which changes to make now vs later, expected impact, and risk."),
        _stage("tech_seo", "Specify the change",
               {}, "A precise `site_control` change spec (op + fields) for each approved item."),
    ]
    return {"goal": f"change: {goal}", "kind": "change", "stages": stages,
            "apply_gate": "autonomy (" + autonomy.mode(cfg) + ") — destructive ops need approval"}


def render_md(cfg, plan):
    L = [f"# Crew — {plan['goal']}",
         f"Run each stage AS the named expert (adopt its standard), passing its deliverable to the next. "
         f"Publish/apply is gated by: {plan.get('publish_gate') or plan.get('apply_gate')}.", ""]
    for i, s in enumerate(plan["stages"], 1):
        L += [f"## Stage {i} · {s['role'].replace('_',' ').title()} — {s['goal']}",
              f"> {s['persona'][:220]}…",
              "**Deliverable:** " + s["deliverable"]]
        if s["inputs"]:
            keys = ", ".join(k for k in s["inputs"])
            L.append(f"_Inputs provided: {keys}._")
        L.append("")
    L.append("_When driven by an agent, spawn a sub-agent per stage (or adopt each persona in turn). "
             "The final stage's output goes through the safety gate and the autonomy mode before anything "
             "touches the live site._")
    return "\n".join(L)
