from flask import Flask, abort

app = Flask(__name__)

@app.route("/mcp/capabilities", methods=["GET"])
def get_capabilities():
    """Return tool capabilities (not yet implemented)."""
    abort(501, description="Not implemented")

@app.route("/mcp/tools/kali_tools/<tool_name>", methods=["POST"])
def execute_tool(tool_name):
    """Direct tool execution (not yet implemented)."""
    abort(501, description="Not implemented")
