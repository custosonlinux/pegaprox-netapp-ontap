# Changelog

All notable changes to this project will be documented in this file.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.9.8] – 2026-05-13

### Added
- **Provisioning tab** — end-to-end iSCSI datastore setup directly from the UI:
  - Wizard (3 steps): protocol/endpoint/SVM → ONTAP volume/LUN/iGroup → PVE hosts/VG/storage ID
  - Reuse existing ONTAP objects (volumes, LUNs, iGroups) or create new ones
  - Linear (thick) and thin-provisioned LVM VG support
  - Automatic per-host iSCSI discovery, login, multipath device wait, pvcreate/vgcreate, pvscan activation, and `pvesm` storage registration
  - Remove datastore: pvesm remove, VG deactivate, iSCSI logout, optional ONTAP LUN/volume delete
- **SnapMirror® visibility** — scan and display SnapMirror relationships per ONTAP endpoint; trigger update transfers; list secondary snapshots
- **SnapMirror DR restore/clone** — restore or clone VMs from a secondary SnapMirror volume (NFS)
- **SAN snapmanifest** — dedicated 64 MB ext4 LV inside the VG stores the VM manifest inside every ONTAP snapshot, enabling restore/clone from ONTAP-native snapshots
- **DR clone** — clone VMs from a SnapMirror secondary directly into the primary cluster
- **Job cancellation** — cancel a running job between steps; automatic cleanup of partial work (temp clones, imported VGs, reserved VMIDs)
- **SMTP / email notifications** — per-schedule notifications on job completion (all / failures only / success only)
- **Multi-VM snapshot** — snapshot multiple VMs on the same mapping in one operation
- **ONTAP-native snapshot visibility** — shows snapshots not created by this plugin; supports restore and clone from them

### Fixed
- **KI-001 resolved** — ASA NVMe: Single VM Restore and Clone now use `POST /api/private/cli/volume/clone` + `protocols/nvme/subsystem-maps` instead of the unavailable REST namespace clone endpoint
- iSCSI WWID formula corrected to NAA type-6 (3 + `600a0980` + hex(serial)) — multipath device was not found with the previous formula
- `flush_iscsi_clone_device`: now uses computed WWID (from serial) instead of sysfs serial read; also flushes SCSI layer via `/proc/scsi/scsi` or `scsi_device` sysfs delete
- iSCSI clone: temp igroup created as single-host igroup to prevent LUN visibility on other cluster nodes during restore/clone
- Route registration in `provisioning.py` migrated from `bp.route()` to `register_plugin_route()` — fixes "No module named pegaprox.core.plugin_router" on fresh installs
- `_execute_schedule`: uses `build_pve_client()` instead of the always-empty `cluster_managers` dict
- `_vms_for_mapping`: uses storage content API instead of listing all cluster VMs
- Retention import path corrected: `from ..core._helpers` (was: `from .._helpers`)

## [0.9.0] – 2026-05-05

### Added
- Full management UI (6 tabs: Snapshots, Schedules, VM-Restore, VM-Clone, Jobs, Settings)
- Internationalization: DE, EN, FR, ES, PT, KO, IT
- VM-Clone via ONTAP File Clone CoW (near-instant, no data transfer)
- Scheduled snapshots with cron expressions, retention policy and SnapMirror labels
- Auto-discovery of ONTAP volumes mapped to Proxmox NFS datastores
- Proxmox host management (standalone hosts without PVE cluster)
- ONTAP-native snapshot visibility (snapshots not created by this plugin)
- Manifest system: VM configs and disk inventory stored inside the snapshot
- Support for Proxmox LXC containers alongside QEMU VMs
- Snapshot consistency levels: crash-consistent, app-consistent (fsfreeze), suspend

### Changed
- Snapshot naming convention: `NPP_{user_input}` for manual, `NPP_{YYYYMMDD}_{HHMM}[_{schedule}]` for scheduled
- Restore and Clone split into separate engines and API routes
- Requires PegaProx ≥ 0.9.9

## [0.2.0] – 2026-04-01

### Added
- Initial snapshot creation and deletion
- Single-VM restore via SFSR (Single-File Snapshot Restore)
- FlexClone-based restore (full copy via qemu-img)
- Basic job tracking

## [0.1.0] – 2026-03-01

### Added
- Initial plugin skeleton
- ONTAP REST API client
- Volume mapping management
