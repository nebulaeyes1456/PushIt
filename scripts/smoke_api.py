# -*- coding: utf-8 -*-
"""PushIt · API 冒烟验收（M2）。纯 urllib，无第三方依赖。

前提：先启动后端
  .venv/Scripts/python -m uvicorn backend.main:app --app-dir . --port 8765
"""
import json
import sys
import urllib.request

BASE = "http://127.0.0.1:8765"


def call(method, path, body=None):
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else b"{}"
    req = urllib.request.Request(BASE + path, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main():
    h = call("GET", "/health")
    assert h["ok"], h
    print("[1/6] health OK, llm configured =", h["llm"])

    rid = call("POST", "/api/v1/requirements",
               {"text": "顺手把报表导出权限也开了，这周一起上",
                "person_id": "pmid", "source": "口头"})["requirement_id"]
    print("[2/6] create ->", rid)

    rep = call("POST", "/api/v1/requirements/" + rid + "/process?use_llm=false", {})
    assert rep["strategy"]["mode"] == "rule", rep["strategy"]
    assert rep["strategy"]["safe_version"], rep["strategy"]
    print("[3/6] process ->", rep["verdict"], "| tactic:", rep["strategy"]["tactic_id"],
          "| est:", rep["estimate"]["total_low"], "~", rep["estimate"]["total_high"])

    res = call("POST", "/api/v1/requirements/" + rid + "/result",
               {"result": "decline", "warded_hours": 3.6})
    assert res["committed"], res
    print("[4/6] result decline OK")

    load = call("GET", "/api/v1/load")
    print("[5/6] load -> committed", load["committed"], "new", load["new_low"], "~",
          load["new_high"], "overload", load["overload"])

    persons = call("GET", "/api/v1/persons")
    assert any(p.get("behavior_counts", {}).get("kick_ball") for p in persons), persons
    print("[6/6] persons -> kick_ball 画像存在 OK")

    print("SMOKE PASS")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as e:
        print("无法连接后端：请先启动 uvicorn（.venv/Scripts/python -m uvicorn "
              "backend.main:app --app-dir . --port 8765）")
        sys.exit(1)
