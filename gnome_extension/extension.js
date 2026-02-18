/**
 * GNOME AI Bridge Extension
 * Registers org.gnome.AIBridge on the session bus so a local daemon
 * (running outside the shell process) can query and control the desktop.
 *
 * Compatible: GNOME Shell 46+
 * Uses Gio.DBusExportedObject.wrapJSObject (the standard GJS pattern).
 */

import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Meta from 'gi://Meta';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';

// ── DBus XML interface definition ──────────────────────────────────────────────
const AI_BRIDGE_IFACE = `
<node>
  <interface name="org.gnome.AIBridge">

    <method name="GetWindows">
      <arg type="s" name="windows_json" direction="out"/>
    </method>

    <method name="FocusWindow">
      <arg type="u" name="window_id" direction="in"/>
      <arg type="b" name="success"   direction="out"/>
    </method>

    <method name="CloseWindow">
      <arg type="u" name="window_id" direction="in"/>
      <arg type="b" name="success"   direction="out"/>
    </method>

    <method name="MoveResizeWindow">
      <arg type="u" name="window_id" direction="in"/>
      <arg type="i" name="x"         direction="in"/>
      <arg type="i" name="y"         direction="in"/>
      <arg type="i" name="width"     direction="in"/>
      <arg type="i" name="height"    direction="in"/>
      <arg type="b" name="success"   direction="out"/>
    </method>

    <method name="MinimizeWindow">
      <arg type="u" name="window_id" direction="in"/>
      <arg type="b" name="success"   direction="out"/>
    </method>

    <method name="MaximizeWindow">
      <arg type="u" name="window_id" direction="in"/>
      <arg type="b" name="maximize"  direction="in"/>
      <arg type="b" name="success"   direction="out"/>
    </method>

    <method name="GetWorkspaces">
      <arg type="s" name="workspaces_json" direction="out"/>
    </method>

    <method name="SwitchWorkspace">
      <arg type="i" name="index"   direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>

    <method name="LaunchApp">
      <arg type="s" name="command" direction="in"/>
      <arg type="b" name="success" direction="out"/>
    </method>

    <method name="GetFocusedWindow">
      <arg type="u" name="window_id" direction="out"/>
    </method>

    <signal name="WindowsChanged">
      <arg type="s" name="windows_json"/>
    </signal>

  </interface>
</node>`;

// ── Helper functions ───────────────────────────────────────────────────────────

function _allWindows() {
    return global.get_window_actors()
        .map(a => a.meta_window)
        .filter(w => w &&
                     !w.is_skip_taskbar() &&
                     w.get_window_type() === Meta.WindowType.NORMAL);
}

function _findWindow(id) {
    return _allWindows().find(w => w.get_id() === id) ?? null;
}

function _windowToJson(w) {
    const rect = w.get_frame_rect();
    const ws   = w.get_workspace();
    let xid = 0;
    try {
        const xw = w.get_x11_window?.();
        if (xw) xid = xw;
    } catch (_) { /* Wayland — no XID */ }

    return {
        id:        w.get_id(),
        xid:       xid,
        title:     w.get_title() ?? '',
        wm_class:  w.get_wm_class() ?? '',
        pid:       w.get_pid(),
        focused:   w.has_focus(),
        minimized: w.minimized,
        maximized: w.get_maximized() !== 0,
        workspace: ws ? ws.index() : -1,
        x:         rect.x,
        y:         rect.y,
        width:     rect.width,
        height:    rect.height,
    };
}

// ── DBus method implementations (plain JS object for wrapJSObject) ─────────
const AIBridgeMethods = {
    GetWindows() {
        try {
            return JSON.stringify(_allWindows().map(_windowToJson));
        } catch (e) {
            logError(e, 'AIBridge.GetWindows');
            return '[]';
        }
    },

    FocusWindow(id) {
        const w = _findWindow(id);
        if (!w) return false;
        try {
            Main.activateWindow(w);
            return true;
        } catch (e) {
            logError(e, 'AIBridge.FocusWindow');
            return false;
        }
    },

    CloseWindow(id) {
        const w = _findWindow(id);
        if (!w) return false;
        try {
            w.delete(global.get_current_time());
            return true;
        } catch (e) {
            logError(e, 'AIBridge.CloseWindow');
            return false;
        }
    },

    MoveResizeWindow(id, x, y, width, height) {
        const w = _findWindow(id);
        if (!w) return false;
        try {
            w.unmaximize(Meta.MaximizeFlags.HORIZONTAL |
                         Meta.MaximizeFlags.VERTICAL);
            w.move_resize_frame(false, x, y, width, height);
            return true;
        } catch (e) {
            logError(e, 'AIBridge.MoveResizeWindow');
            return false;
        }
    },

    MinimizeWindow(id) {
        const w = _findWindow(id);
        if (!w) return false;
        try { w.minimize(); return true; }
        catch (_) { return false; }
    },

    MaximizeWindow(id, maximize) {
        const w = _findWindow(id);
        if (!w) return false;
        try {
            if (maximize)
                w.maximize(Meta.MaximizeFlags.HORIZONTAL |
                           Meta.MaximizeFlags.VERTICAL);
            else
                w.unmaximize(Meta.MaximizeFlags.HORIZONTAL |
                             Meta.MaximizeFlags.VERTICAL);
            return true;
        } catch (_) { return false; }
    },

    GetWorkspaces() {
        try {
            const mgr    = global.workspace_manager;
            const count  = mgr.get_n_workspaces();
            const active = mgr.get_active_workspace_index();
            const data   = [];
            for (let i = 0; i < count; i++)
                data.push({index: i, active: i === active});
            return JSON.stringify(data);
        } catch (e) {
            logError(e, 'AIBridge.GetWorkspaces');
            return '[]';
        }
    },

    SwitchWorkspace(index) {
        try {
            const mgr = global.workspace_manager;
            if (index < 0 || index >= mgr.get_n_workspaces()) return false;
            mgr.get_workspace_by_index(index)
               .activate(global.get_current_time());
            return true;
        } catch (e) {
            logError(e, 'AIBridge.SwitchWorkspace');
            return false;
        }
    },

    LaunchApp(command) {
        try {
            const info = Gio.AppInfo.create_from_commandline(
                command, null, Gio.AppInfoCreateFlags.NONE);
            info.launch([], null);
            return true;
        } catch (_) {
            try {
                Gio.Subprocess.new(
                    ['/bin/sh', '-c', command],
                    Gio.SubprocessFlags.NONE);
                return true;
            } catch (e2) {
                logError(e2, 'AIBridge.LaunchApp');
                return false;
            }
        }
    },

    GetFocusedWindow() {
        const fw = global.display.get_focus_window();
        return fw ? fw.get_id() : 0;
    },
};

// ── Extension class ────────────────────────────────────────────────────────────
export default class AIBridgeExtension extends Extension {

    enable() {
        this._dbusObj = null;
        this._nameId  = null;

        // Wrap the plain JS object as a DBus exported object
        this._dbusObj = Gio.DBusExportedObject.wrapJSObject(
            AI_BRIDGE_IFACE, AIBridgeMethods);

        // Own the well-known bus name; export the object once we have a connection
        this._nameId = Gio.bus_own_name(
            Gio.BusType.SESSION,
            'org.gnome.AIBridge',
            Gio.BusNameOwnerFlags.NONE,
            (connection, _name) => {   // on_bus_acquired
                try {
                    this._dbusObj.export(connection, '/org/gnome/AIBridge');
                    log('AIBridge: exported on session bus');
                } catch (e) {
                    logError(e, 'AIBridge: export failed');
                }
            },
            null,  // on_name_acquired
            () => log('AIBridge: could not own bus name'),
        );

        // Watch window-list changes (emit DBus signal)
        this._sigDisplay = global.display.connect(
            'window-created', this._emitWindowsChanged.bind(this));
        this._sigWM = global.window_manager.connect(
            'destroy', this._emitWindowsChanged.bind(this));

        log('AIBridge extension enabled');
    }

    disable() {
        // Disconnect window signals correctly from their source
        if (this._sigDisplay) {
            global.display.disconnect(this._sigDisplay);
            this._sigDisplay = null;
        }
        if (this._sigWM) {
            global.window_manager.disconnect(this._sigWM);
            this._sigWM = null;
        }

        // Unexport the DBus object
        if (this._dbusObj) {
            try { this._dbusObj.unexport(); } catch (_) {}
            this._dbusObj = null;
        }

        // Release the bus name
        if (this._nameId) {
            Gio.bus_unown_name(this._nameId);
            this._nameId = null;
        }

        log('AIBridge extension disabled');
    }

    _emitWindowsChanged() {
        if (!this._dbusObj) return;
        try {
            const data = AIBridgeMethods.GetWindows();
            this._dbusObj.emit_signal(
                'WindowsChanged',
                new GLib.Variant('(s)', [data]),
            );
        } catch (e) {
            logError(e, 'AIBridge._emitWindowsChanged');
        }
    }
}
