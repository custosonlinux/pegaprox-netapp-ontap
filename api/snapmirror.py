"""
SnapMirror® API

  snapmirror/scan               POST  – scan relationships
  snapmirror/relationships      GET   – cached relationships
  snapmirror/update             POST  – trigger manual update
  snapmirror/secondary-snapshots GET  – snapshots on secondary volume
  snapmirror/ensure-export      POST  – ensure NFS export on secondary
"""

import logging
from flask import request
from pegaprox.core.db import get_db
from pegaprox.api.plugins import register_plugin_route

log = logging.getLogger(__name__)
from ..core._helpers import PLUGIN_ID  # noqa: F401


def _require_admin():
    from pegaprox.utils.auth import load_users
    from pegaprox.models.permissions import ROLE_ADMIN
    username = request.session.get("user", "")
    users = load_users()
    if users.get(username, {}).get("role") != ROLE_ADMIN:
        return {"error": "Admin access required"}, 403
    return None


def _scan_relationships():
    err = _require_admin()
    if err:
        return err
    from ..core.snapmirror import scan_relationships
    db = get_db()
    found, errors = scan_relationships(db)
    return {"success": True, "found": found, "errors": errors}


def _list_relationships():
    db = get_db()
    rows = db.query(
        "SELECT r.*, ep_src.name AS source_endpoint_name, ep_dst.name AS dest_endpoint_name "
        "FROM netapp_snapmirror_relationships r "
        "LEFT JOIN netapp_endpoints ep_src ON ep_src.id = r.source_endpoint_id "
        "LEFT JOIN netapp_endpoints ep_dst ON ep_dst.id = r.dest_endpoint_id "
        "ORDER BY r.source_volume, r.dest_volume"
    )
    return [dict(r) for r in (rows or [])]


def _update_relationship():
    err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    relationship_id = data.get("relationship_id")
    if not relationship_id:
        return {"error": "relationship_id required"}, 400

    db = get_db()
    rel = db.query_one(
        "SELECT * FROM netapp_snapmirror_relationships WHERE id=?", (relationship_id,)
    )
    if not rel:
        return {"error": "Relationship not found"}, 404
    rel = dict(rel)

    from ..core._helpers import get_endpoint, build_ontap_client
    try:
        # Start transfer from destination cluster (UUID is known there)
        ep_id = rel.get("dest_endpoint_id") or rel["source_endpoint_id"]
        ep = get_endpoint(db, ep_id)
        client = build_ontap_client(ep)
        job_uuid = client.trigger_snapmirror_transfer(rel["relationship_uuid"])
        return {"success": True, "job_uuid": job_uuid}
    except Exception as exc:
        return {"error": str(exc)}, 500


def _secondary_snapshots():
    relationship_id = request.args.get("relationship_id")
    if not relationship_id:
        return {"error": "relationship_id required"}, 400

    db = get_db()
    from ..core.snapmirror import get_secondary_snapshots
    try:
        snaps, rel = get_secondary_snapshots(db, relationship_id)
        return {
            "snapshots": snaps,
            "relationship": {
                "id": rel["id"],
                "dest_volume": rel["dest_volume"],
                "dest_svm": rel["dest_svm"],
                "dest_cluster_name": rel["dest_cluster_name"],
                "dest_nfs_ip": rel["dest_nfs_ip"],
                "dest_junction_path": rel["dest_junction_path"],
            },
        }
    except Exception as exc:
        return {"error": str(exc)}, 500


def _ensure_export():
    err = _require_admin()
    if err:
        return err
    data = request.get_json() or {}
    relationship_id = data.get("relationship_id")
    if not relationship_id:
        return {"error": "relationship_id required"}, 400

    db = get_db()
    from ..core.snapmirror import ensure_secondary_nfs_export
    try:
        nfs_ip, junction, created = ensure_secondary_nfs_export(db, relationship_id)
        return {
            "success": True,
            "nfs_ip": nfs_ip,
            "junction_path": junction,
            "rule_created": created,
        }
    except Exception as exc:
        return {"error": str(exc)}, 500


def register_routes():
    register_plugin_route(PLUGIN_ID, "snapmirror/scan", _scan_relationships)
    register_plugin_route(PLUGIN_ID, "snapmirror/relationships", _list_relationships)
    register_plugin_route(PLUGIN_ID, "snapmirror/update", _update_relationship)
    register_plugin_route(PLUGIN_ID, "snapmirror/secondary-snapshots", _secondary_snapshots)
    register_plugin_route(PLUGIN_ID, "snapmirror/ensure-export", _ensure_export)
