#!/usr/bin/env python3
"""
Claude Code project dashboard -- display + rotation selection only.

All the round-robin scanning/switching logic lives in scheduler.py, a
separate always-on process. This app just:
  - shows each project's status (git, pending request count)
  - shows which project the scheduler currently has active, and its phase
    (processing / waiting / hibernating)
  - lets you tick which projects are in the scheduler's rotation pool
  - shows a recent activity log (when things last got picked up)
  - if a project has left SQL to run (e.g. for Supabase) in
    .claude-status/sql_output.txt, shows it in a copyable window

Run:
  python3 dashboard.py
Then open http://<pi-ip>:8420
"""

import os
import signal
import subprocess
import threading
import time

from flask import Flask, abort, jsonify, render_template, request, send_file

import common
import fleet_db

app = Flask(__name__)

# Used by /api/admin/status to tell whether a source file has changed since
# this process came up (Flask runs with debug=False, no autoreload).
START_TIME = time.time()


# ---- Routes -------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", version=common.app_version(), theme=common.load_theme())


@app.route("/help")
def help_page():
    return render_template("help.html")


@app.route("/help-simple")
def help_simple_page():
    return render_template("help_simple.html")


@app.route("/api/status")
def api_status():
    scheduler = common.load_scheduler_state()
    selected = set(common.load_selected())
    # active_projects is the current schema (scheduler can run more than one
    # project at once); fall back to the older single-project fields in case
    # this ever reads a state file written by a pre-concurrency scheduler.
    active_projects = scheduler.get("active_projects")
    if active_projects is None:
        legacy_active = scheduler.get("active_project")
        active_projects = (
            [{"project": legacy_active, "phase": scheduler.get("phase"), "pending": scheduler.get("pending")}]
            if legacy_active else []
        )
    active_by_name = {a["project"]: a for a in active_projects}

    projects = []
    for name in common.list_projects():
        status = common.read_status(name)
        ready, total = common.scan_requests(name)
        sql_path = common.find_sql_output(name)
        active_info = active_by_name.get(name)
        active_processing = active_info is not None and active_info.get("phase") == "processing"
        projects.append({
            "name": name,
            "in_rotation": name in selected,
            "is_active": active_info is not None,
            "phase": active_info.get("phase") if active_info else None,
            "current_task": status.get("current_task"),
            "last_active_relative": common.relative_time(status.get("last_active")),
            "pending_requests": ready,
            "total_requests": total,
            "requests": common.list_requests(name, active_processing),
            "last_commit": common.last_commit(name),
            "has_sql": sql_path is not None,
            "sql_updated_relative": common.file_mtime_relative(sql_path) if sql_path else None,
        })

    return jsonify({
        "active_projects": [a["project"] for a in active_projects],
        # First active project, kept for older clients reading a single field.
        "active_project": active_projects[0]["project"] if active_projects else None,
        "phase": active_projects[0]["phase"] if active_projects else scheduler.get("phase"),
        "scheduler_last_update": scheduler.get("last_update"),
        "projects": projects,
    })


@app.route("/api/selected", methods=["POST"])
def api_select():
    data = request.get_json(force=True)
    project = data.get("project")
    want_selected = bool(data.get("selected"))

    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404

    selected = common.load_selected()
    if want_selected and project not in selected:
        selected.append(project)
    elif not want_selected and project in selected:
        selected.remove(project)
    common.save_selected(selected)
    return jsonify({"ok": True, "selected": selected})


@app.route("/api/requests/<project>", methods=["POST"])
def api_create_request(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404

    title = (request.form.get("title") or "").strip()
    if not title:
        return jsonify({"ok": False, "error": "title is required"}), 400
    content = (request.form.get("content") or "").strip()
    if not content:
        return jsonify({"ok": False, "error": "content is required"}), 400
    ready = request.form.get("ready") == "1"
    attachments = [f for f in request.files.getlist("attachments") if f.filename]

    if attachments:
        folder = common.create_request_folder(project, title, content, ready, attachments)
        common.log_event(project, "request_created", detail=folder.name)
        return jsonify({"ok": True, "created": folder.name, "kind": "folder"})

    path = common.create_request_file(project, title, content, ready)
    common.log_event(project, "request_created", detail=path.name)
    return jsonify({"ok": True, "created": path.name, "kind": "file"})


@app.route("/api/requests/<project>/ready", methods=["POST"])
def api_request_ready(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if not common.set_request_ready(project, name):
        return jsonify({"ok": False, "error": "request not found"}), 404
    common.log_event(project, "request_marked_ready", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/not-ready", methods=["POST"])
def api_request_not_ready(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    snapshot = common.tmux_capture(project) if common.tmux_alive(project) else None
    if not common.set_request_not_ready(project, name, console_snapshot=snapshot):
        return jsonify({"ok": False, "error": "request not found"}), 404
    common.log_event(project, "request_marked_not_ready", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/content")
def api_request_content(project):
    if project not in common.list_projects():
        abort(404)
    name = request.args.get("name") or ""
    body = common.read_request_body(project, name)
    if body is None:
        return jsonify({"ok": False, "error": "request not found"}), 404
    return jsonify({"ok": True, "content": body})


@app.route("/api/requests/<project>/content", methods=["POST"])
def api_request_content_save(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    content = data.get("content")
    if not name or not (content or "").strip():
        return jsonify({"ok": False, "error": "name and content are required"}), 400
    if not common.write_request_body(project, name, content):
        return jsonify({"ok": False, "error": "request not found"}), 404
    common.log_event(project, "request_edited", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/shelve", methods=["POST"])
def api_request_shelve(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if not common.shelve_request(project, name):
        return jsonify({"ok": False, "error": "request not found"}), 404
    common.log_event(project, "request_shelved", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/shelved/list")
def api_requests_shelved_list(project):
    if project not in common.list_projects():
        abort(404)
    return jsonify({"shelved": common.list_shelved(project)})


@app.route("/api/requests/<project>/shelved/unshelve", methods=["POST"])
def api_request_unshelve(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if not common.unshelve_request(project, name):
        return jsonify({"ok": False, "error": "shelved request not found"}), 404
    common.log_event(project, "request_unshelved", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/shelved/delete", methods=["POST"])
def api_request_shelved_delete(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"ok": False, "error": "name is required"}), 400
    if not common.delete_shelved_request(project, name):
        return jsonify({"ok": False, "error": "shelved request not found"}), 404
    common.log_event(project, "request_shelved_deleted", detail=name)
    return jsonify({"ok": True})


@app.route("/api/requests/<project>/list")
def api_requests_list(project):
    if project not in common.list_projects():
        abort(404)
    scheduler = common.load_scheduler_state()
    active_projects = scheduler.get("active_projects")
    if active_projects is None:
        legacy_active = scheduler.get("active_project")
        active_projects = (
            [{"project": legacy_active, "phase": scheduler.get("phase")}] if legacy_active else []
        )
    active_processing = any(
        a["project"] == project and a.get("phase") == "processing"
        for a in active_projects
    )
    return jsonify({"requests": common.list_requests(project, active_processing)})


def _is_console_target(project):
    return project == common.INDEPENDENT_SESSION or project in common.list_projects()


@app.route("/api/console/<project>")
def api_console(project):
    if not _is_console_target(project):
        abort(404)
    alive = common.tmux_alive(project)
    content = common.tmux_capture(project) if alive else None
    return jsonify({"alive": alive, "content": content})


@app.route("/api/console/<project>/send", methods=["POST"])
def api_console_send(project):
    if not _is_console_target(project):
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"ok": False, "error": "text is required"}), 400
    if not common.tmux_send(project, text):
        return jsonify({"ok": False, "error": "no active session for this project"}), 409
    return jsonify({"ok": True})


@app.route("/api/console/<project>/key", methods=["POST"])
def api_console_key(project):
    if not _is_console_target(project):
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    key = (data.get("key") or "").strip()
    if key not in common.ALLOWED_CONSOLE_KEYS:
        return jsonify({"ok": False, "error": "key not allowed"}), 400
    if not common.tmux_send_key(project, key):
        return jsonify({"ok": False, "error": "no active session for this project"}), 409
    return jsonify({"ok": True})


@app.route("/api/archive/<project>")
def api_archive_list(project):
    if project not in common.list_projects():
        abort(404)
    subpath = request.args.get("path", "")
    entries = common.list_archive(project, subpath)
    if entries is None:
        return jsonify({"entries": [], "found": False})
    return jsonify({"entries": entries, "found": True})


@app.route("/api/archive/<project>/file")
def api_archive_file(project):
    if project not in common.list_projects():
        abort(404)
    rel_path = request.args.get("path", "")
    if not rel_path:
        return jsonify({"error": "path is required"}), 400
    result = common.read_archive_file(project, rel_path)
    if result is None:
        abort(404)
    return jsonify(result)


@app.route("/api/archive/<project>/raw")
def api_archive_raw(project):
    if project not in common.list_projects():
        abort(404)
    rel_path = request.args.get("path", "")
    if not rel_path:
        abort(400)
    target = common.resolve_archive_file(project, rel_path)
    if target is None:
        abort(404)
    return send_file(target)


@app.route("/project/<project>")
def project_detail(project):
    if project not in common.list_projects():
        abort(404)
    return render_template("project.html", project=project)


@app.route("/api/project/<project>/files")
def api_project_files(project):
    if project not in common.list_projects():
        abort(404)
    proj_dir = common.PROJECTS_DIR / project
    description = common.find_description_file(project)
    agent_files = common.list_agent_files(project)
    return jsonify({
        "description": (
            {"path": str(description.relative_to(proj_dir)), "name": description.name}
            if description else None
        ),
        "agent_files": [
            {"path": str(p.relative_to(proj_dir)), "name": p.name}
            for p in agent_files
        ],
        "has_github": common.has_github_remote(project),
    })


@app.route("/api/project/<project>/file")
def api_project_file(project):
    if project not in common.list_projects():
        abort(404)
    rel_path = request.args.get("path", "")
    if not rel_path:
        return jsonify({"error": "path is required"}), 400
    content = common.read_project_file(project, rel_path)
    if content is None:
        abort(404)
    return jsonify({"content": content})


@app.route("/api/project/<project>/description", methods=["POST"])
def api_project_description_save(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    data = request.get_json(force=True) or {}
    content = data.get("content")
    if content is None:
        return jsonify({"ok": False, "error": "content is required"}), 400
    if not common.write_description_file(project, content):
        return jsonify({"ok": False, "error": "failed to write file"}), 500
    common.log_event(project, "description_edited")
    return jsonify({"ok": True})


@app.route("/api/project/<project>/git/status")
def api_project_git_status(project):
    if project not in common.list_projects():
        abort(404)
    if not common.has_github_remote(project):
        return jsonify({"has_github": False})
    return jsonify({"has_github": True, "changes": common.git_status(project) or []})


@app.route("/api/project/<project>/git/log")
def api_project_git_log(project):
    if project not in common.list_projects():
        abort(404)
    if not common.has_github_remote(project):
        return jsonify({"has_github": False})
    return jsonify({"has_github": True, "commits": common.git_log(project) or []})


@app.route("/api/project/<project>/git/commit", methods=["POST"])
def api_project_git_commit(project):
    if project not in common.list_projects():
        return jsonify({"ok": False, "error": "unknown project"}), 404
    if not common.has_github_remote(project):
        return jsonify({"ok": False, "error": "not a GitHub project"}), 400
    data = request.get_json(force=True) or {}
    message = data.get("message", "")
    result = common.git_commit_and_push(project, message)
    if result.get("ok"):
        common.log_event(project, "git_commit_push", detail=message.strip()[:200])
    return jsonify(result)


@app.route("/api/log")
def api_log():
    project = request.args.get("project") or None
    limit = min(int(request.args.get("limit", 50)), 200)
    return jsonify({"entries": common.read_log(limit=limit, project=project)})


@app.route("/api/proc-status")
def api_proc_status():
    """One-glance view of where request processing is right now: which
    project sessions are alive, what each pane is doing, what's still
    pending, and which look stuck. Backs the Processing tab.

    "stuck" = the project still has READY requests and a live session, but
    the pane isn't producing output and isn't showing Claude Code's
    "working" indicator -- i.e. it's most likely parked on an interactive
    prompt without having set the request to WAITING RESPONSE.
    """
    scheduler = common.load_scheduler_state()
    active = {a["project"]: a for a in (scheduler.get("active_projects") or [])}
    sessions = {s["project"]: s for s in common.list_project_sessions()}
    selected = set(common.load_selected())

    names = set(sessions) | set(active) | selected
    projects = []
    for name in sorted(names):
        ready, total = common.scan_requests(name)
        sess = sessions.get(name)
        phase = active[name].get("phase") if name in active else None
        stuck = bool(ready > 0 and sess is not None and sess["state"] != "working")
        projects.append({
            "name": name,
            "in_rotation": name in selected,
            "phase": phase,
            "session_alive": sess is not None,
            "session_state": sess["state"] if sess else None,
            "session_moved": sess["moved"] if sess else None,
            "pending_requests": ready,
            "total_requests": total,
            "requests": common.list_requests(name, phase == "processing"),
            "tail": sess["tail"] if sess else None,
            "stuck": stuck,
        })

    return jsonify({
        "scheduler_last_update": scheduler.get("last_update"),
        "scheduler_last_update_relative": common.relative_time(scheduler.get("last_update")),
        "rotation_pool": scheduler.get("rotation_pool", []),
        "activity_log": common.read_log(limit=30),
        "projects": projects,
    })


@app.route("/api/sql/<project>")
def api_sql_get(project):
    if project not in common.list_projects():
        abort(404)
    sql_path = common.find_sql_output(project)
    if sql_path is None:
        return jsonify({"content": None})
    try:
        content = sql_path.read_text()
    except OSError:
        abort(500)
    return jsonify({
        "content": content,
        "filename": sql_path.name,
        "updated": common.file_mtime_relative(sql_path),
    })


@app.route("/api/sql/<project>/clear", methods=["POST"])
def api_sql_clear(project):
    if project not in common.list_projects():
        abort(404)
    sql_path = common.find_sql_output(project)
    if sql_path is not None:
        try:
            sql_path.unlink()
        except OSError:
            abort(500)
    return jsonify({"ok": True})


@app.route("/api/admin/theme")
def api_admin_theme():
    return jsonify({"theme": common.load_theme(), "defaults": common.DEFAULT_THEME})


@app.route("/api/admin/theme", methods=["POST"])
def api_admin_theme_save():
    data = request.get_json(force=True) or {}
    overrides = data.get("theme")
    if not isinstance(overrides, dict):
        return jsonify({"ok": False, "error": "theme object is required"}), 400
    try:
        theme = common.save_theme(overrides)
    except ValueError as e:
        return jsonify({"ok": False, "error": str(e)}), 400
    common.log_event("BdRDev", "theme_updated")
    return jsonify({"ok": True, "theme": theme})


@app.route("/api/admin/theme/reset", methods=["POST"])
def api_admin_theme_reset():
    theme = common.save_theme({})
    common.log_event("BdRDev", "theme_reset")
    return jsonify({"ok": True, "theme": theme})


@app.route("/api/ecosystem")
def api_ecosystem():
    # Try Supabase first; fall back to the JSON cache when it's not
    # configured or unreachable. fetch_ecosystem() refreshes the JSON
    # cache itself on a successful read.
    eco = fleet_db.fetch_ecosystem()
    source = "supabase"
    if eco is None:
        eco = common.load_ecosystem()
        source = "json-fallback"
    return jsonify({
        "ecosystem": eco,
        "options": common.ECOSYSTEM_FIELD_OPTIONS,
        "source": source,
        "supabase_configured": fleet_db.is_configured(),
        "fallback_reason": None if source == "supabase" else fleet_db.last_error(),
    })


@app.route("/api/ecosystem", methods=["POST"])
def api_ecosystem_save():
    data = request.get_json(force=True) or {}
    eco = data.get("ecosystem")
    if not isinstance(eco, dict):
        return jsonify({"ok": False, "error": "ecosystem object is required"}), 400
    # Push to Supabase if we can; always keep the JSON file in sync so it
    # stays a usable fallback whether or not the DB write landed.
    source = "supabase" if fleet_db.push_ecosystem(eco) else "json-fallback"
    saved = common.save_ecosystem(eco)
    common.log_event("BdRDev", "ecosystem_updated")
    return jsonify({
        "ok": True, "ecosystem": saved, "source": source,
        "supabase_configured": fleet_db.is_configured(),
        "fallback_reason": None if source == "supabase" else fleet_db.last_error(),
    })


@app.route("/api/admin/status")
def api_admin_status():
    return jsonify({
        "needs_restart": common.dashboard_needs_restart(START_TIME),
        "scheduler_needs_restart": common.scheduler_needs_restart(),
        "scheduler_running": _scheduler_pid() is not None,
    })


@app.route("/api/admin/restart", methods=["POST"])
def api_admin_restart():
    common.log_event("BdRDev", "dashboard_restart_requested")

    def _kill_self():
        # Give the response time to flush before the process dies. SIGKILL
        # (not SIGTERM) is required -- systemd's Restart=on-failure treats
        # SIGTERM as an intentional stop and won't relaunch it.
        time.sleep(0.3)
        os.kill(os.getpid(), signal.SIGKILL)

    threading.Thread(target=_kill_self, daemon=True).start()
    return jsonify({"ok": True})


def _scheduler_pid():
    """PID of the running scheduler.py process, or None. The dashboard has
    no in-process handle on it (separate systemd service), so it's found
    by matching the command line. Anchored to the end of the line (not
    just a bare "app/scheduler.py" substring) so a shell command that
    merely *mentions* that path -- e.g. someone editing/grepping the
    file -- can't be mistaken for the process itself."""
    pattern = str(common.APP_DIR / "scheduler.py") + "$"
    try:
        out = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True, text=True, timeout=5,
        ).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for line in out.splitlines():
        try:
            return int(line.strip())
        except ValueError:
            continue
    return None


@app.route("/api/admin/restart_scheduler", methods=["POST"])
def api_admin_restart_scheduler():
    common.log_event("BdRDev", "scheduler_restart_requested")
    pid = _scheduler_pid()
    if pid is None:
        return jsonify({"ok": False, "error": "scheduler process not found"}), 404
    try:
        # SIGKILL, not SIGTERM -- same reasoning as the dashboard's own
        # self-restart: systemd's Restart=on-failure only relaunches on a
        # non-clean exit.
        os.kill(pid, signal.SIGKILL)
    except OSError as e:
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8420, debug=False)
