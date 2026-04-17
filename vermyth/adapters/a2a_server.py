"""Run A2A JSON-RPC (Starlette) server — requires: pip install -e .[a2a]"""

from __future__ import annotations

import argparse
import os

from vermyth.bootstrap import build_tools
from vermyth.mcp.server import TOOL_DISPATCH
from vermyth.mcp.tool_definitions import TOOL_DEFINITIONS


def main() -> None:
    try:
        import uvicorn
    except ImportError as exc:
        raise SystemExit(
            "uvicorn is required for vermyth-a2a. Install: pip install -e .[a2a]"
        ) from exc

    parser = argparse.ArgumentParser(prog="vermyth-a2a")
    parser.add_argument("--host", default=os.environ.get("VERMYTH_A2A_HOST", "127.0.0.1"))
    parser.add_argument("--port", type=int, default=int(os.environ.get("VERMYTH_A2A_PORT", "7788")))
    parser.add_argument("--db", default=None)
    args = parser.parse_args()

    public = os.environ.get(
        "VERMYTH_A2A_PUBLIC_URL",
        f"http://{args.host}:{args.port}",
    )
    os.environ["VERMYTH_A2A_PUBLIC_URL"] = public

    _grimoire, _c, _e, tools = build_tools(db_path=args.db)
    from vermyth.adapters.a2a.sdk_factory import build_a2a_starlette_app

    app = build_a2a_starlette_app(
        tools=tools,
        tool_dispatch=TOOL_DISPATCH,
        tool_definitions=list(TOOL_DEFINITIONS),
        agent_base_url=public,
    )
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
