import datetime, sys, threading, time
import flet as ft
from rs_multiple_master_functions import Master, send_command

def main(page: ft.Page, master: Master):
    page.title = "Multi-Worker Remote-Takeover Monitor"
    page.window_width = 1280
    page.window_height = 800
    page.bgcolor = ft.Colors.GREY_100
    row_blue_grey = ft.Colors.BLUE_GREY_300
    selected_color = ft.Colors.BLUE_GREY_600
    text_dark = ft.Colors.GREY_900

    def border_bottom(width: float, color: str):
        return ft.Border(bottom=ft.BorderSide(width, color))

    def timestamp():
        return datetime.datetime.now().strftime("%H:%M:%S")

    selected_worker_id = {"value": None}   # int worker_id, or None
    row_lookup = {}      # worker_id -> row Container
    row_meta = {}        # worker_id -> {"is_blue": bool, "name_text": Text, "address": str}
    worker_order = []    # ordered list of worker_ids, mirrors worker_list.controls
    # --- worker rows (plain Row-based list instead of DataTable, for full row styling control) ---
    worker_list = ft.Column(spacing=0)

    def repaint_row(worker_id: int):
        row = row_lookup.get(worker_id)
        meta = row_meta.get(worker_id)
        if row is None or meta is None:
            return
        is_selected = (selected_worker_id["value"] == worker_id)
        bg = selected_color if is_selected else (row_blue_grey if meta["is_blue"] else ft.Colors.WHITE)
        text_color = ft.Colors.WHITE if is_selected else text_dark
        for control in row.content.controls:
            control.color = text_color
        row.bgcolor = bg

    def select_worker(worker_id: int):
        previous = selected_worker_id["value"]
        if previous == worker_id:
            # second click on the same row: deselect, revert to original color
            selected_worker_id["value"] = None
            repaint_row(worker_id)
            add_log_line(f"[{timestamp()}] Worker {worker_id} deselected.")
        else:
            selected_worker_id["value"] = worker_id
            if previous is not None:
                repaint_row(previous)
            repaint_row(worker_id)
            add_log_line(f"[{timestamp()}] Worker {worker_id} selected.")
        page.update()

    def make_worker_row(worker_id: int, name: str, address: str, port: str, is_blue: bool):
        name_text = ft.Text(name, color=text_dark, weight=ft.FontWeight.W_600, width=220)
        row_meta[worker_id] = {"is_blue": is_blue, "name_text": name_text, "address": address}
        bg = row_blue_grey if is_blue else ft.Colors.WHITE
        row_container = ft.Container(
            content=ft.Row(
                [
                    ft.Text(str(worker_id), color=text_dark, font_family="Consolas", width=60),
                    name_text,
                    ft.Text(address, color=text_dark, font_family="Consolas", width=220),
                    ft.Text(port, color=text_dark, font_family="Consolas"),
                ],
            ),
            bgcolor=bg,
            padding=ft.Padding(left=16, right=16, top=14, bottom=14),
            border=border_bottom(1, ft.Colors.GREY_300),
            on_click=lambda e, wid=worker_id: select_worker(wid),
            ink=True,
        )
        row_lookup[worker_id] = row_container
        return row_container

    column_headers = ft.Container(
        content=ft.Row(
            [
                ft.Text("ID", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600, width=60),
                ft.Text("NAME", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600, width=220),
                ft.Text("IP ADDRESS", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600, width=220),
                ft.Text("PORT", size=12, weight=ft.FontWeight.BOLD, color=ft.Colors.GREY_600),
            ]
        ),
        padding=ft.Padding(left=16, right=16, top=10, bottom=10),
    )

    def reflow_stripes():
        for index, worker_id in enumerate(worker_order):
            meta = row_meta[worker_id]
            meta["is_blue"] = (index % 2 == 0)
            repaint_row(worker_id)

    # --- adding / removing rows to mirror master's worker dict ---
    def add_worker_row(worker_id: int, name: str, address: str, port: str = "—"):
        if worker_id in row_lookup:
            return
        worker_order.append(worker_id)
        index = len(worker_order) - 1
        is_blue = (index % 2 == 0)
        worker_list.controls.append(make_worker_row(worker_id, name, address, port, is_blue))
        page.update()

    def remove_worker_row(worker_id: int):
        row = row_lookup.pop(worker_id, None)
        row_meta.pop(worker_id, None)
        if worker_id in worker_order:
            worker_order.remove(worker_id)
        if row is not None and row in worker_list.controls:
            worker_list.controls.remove(row)
        if selected_worker_id["value"] == worker_id:
            selected_worker_id["value"] = None
        reflow_stripes()
        page.update()

    # --- header actions: act on whichever worker is currently selected ---
    def remove_worker(e=None):
        worker_id = selected_worker_id["value"]
        if worker_id is None:
            return
        master.remove_worker(worker_id)  # closes the socket, sends exit, drops from master
        remove_worker_row(worker_id)
        add_log_line(f"[{timestamp()}] Worker {worker_id} removed.")

    def close_rename_dialog(e=None):
        rename_dialog.open = False
        page.update()

    def confirm_rename(e=None):
        worker_id = selected_worker_id["value"]
        new_name = rename_input.value.strip()
        close_rename_dialog()
        if worker_id is None or not new_name:
            return
        if master.rename_worker(worker_id, new_name):
            row_meta[worker_id]["name_text"].value = new_name
            add_log_line(f"[{timestamp()}] Worker {worker_id} renamed to {new_name}")
            page.update()
        else:
            add_log_line(f"[{timestamp()}] No worker with ID {worker_id}")

    rename_input = ft.TextField(label="New name", autofocus=True)
    rename_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Rename worker"),
        content=rename_input,
        actions=[
            ft.TextButton("Cancel", on_click=close_rename_dialog),
            ft.TextButton("Rename", on_click=confirm_rename),
        ],
    )
    page.overlay.append(rename_dialog)

    def rename_worker(e=None):
        worker_id = selected_worker_id["value"]
        if worker_id is None:
            return
        rename_input.value = ""
        rename_dialog.open = True
        page.update()

    def handle_send_command(e=None):
        worker_id = selected_worker_id["value"]
        command = command_input.value.strip()
        command_input.value = ""
        page.update()

        if worker_id is None:
            add_log_line(f"[{timestamp()}] No worker selected — command not sent.")
            return
        if not command:
            return

        meta = row_meta.get(worker_id, {})
        worker_name = meta["name_text"].value if "name_text" in meta else f"Worker-{worker_id}"
        add_log_line(f"[{timestamp()}] Master -> {worker_name}: {command}")
        add_log_line(send_command(master, worker_id, command))

    command_input = ft.TextField(
        hint_text="Type a command and press Enter",
        text_style=ft.TextStyle(font_family="Consolas", size=13, color=ft.Colors.GREEN_200),
        hint_style=ft.TextStyle(font_family="Consolas", size=13, color=ft.Colors.GREY_500),
        bgcolor=ft.Colors.BLUE_GREY_900,
        border_color=ft.Colors.BLUE_GREY_700,
        focused_border_color=ft.Colors.GREEN_400,
        cursor_color=ft.Colors.GREEN_400,
        content_padding=ft.Padding(left=10, right=10, top=8, bottom=8),
        on_submit=handle_send_command,
    )

    def quit_server(e=None):
        add_log_line(f"[{timestamp()}] Shutting down server.")
        sys.exit(0)

    BTN_STYLE = ft.ButtonStyle(
        color=ft.Colors.BLUE_GREY_900,
        side=ft.BorderSide(1, ft.Colors.BLUE_GREY_900),
        shape=ft.RoundedRectangleBorder(radius=0),
        padding=ft.Padding(left=10, right=10, top=4, bottom=4),
        text_style=ft.TextStyle(size=12),
    )

    header = ft.Row(
        [
            ft.Text("WORKERS", size=22, weight=ft.FontWeight.BOLD, color=text_dark),
            ft.Container(expand=True),
            ft.OutlinedButton("Rename worker", on_click=rename_worker, style=BTN_STYLE),
            ft.OutlinedButton("Remove worker", on_click=remove_worker, style=BTN_STYLE),
            ft.OutlinedButton("Quit server", on_click=quit_server, style=BTN_STYLE),
        ],
        alignment=ft.MainAxisAlignment.START,
        spacing=6,
    )

    left_panel = ft.Container(
        content=ft.Column(
            [header, ft.Divider(height=1, color=ft.Colors.GREY_300), column_headers, worker_list],
            spacing=10,
        ),
        bgcolor=ft.Colors.GREY_100,
        padding=20,
        expand=True,
    )

    log_view = ft.ListView(expand=True, spacing=2, auto_scroll=True)

    right_panel = ft.Container(
        content=ft.Column(
            [
                ft.Text("Live Log", size=20, color=ft.Colors.GREEN_400, weight=ft.FontWeight.BOLD),
                log_view,
                command_input,
            ],
            expand=True,
        ),
        bgcolor=ft.Colors.BLUE_GREY_900,
        padding=15,
        width=500,
    )

    page.add(
        ft.Row(
            [left_panel, right_panel],
            expand=True,
            spacing=0,
        )
    )

    def add_log_line(text: str):
        log_view.controls.append(
            ft.Text(text, size=12, font_family="Consolas", color=ft.Colors.GREEN_200)
        )
        page.update()

    # --- populate from whatever workers are already connected ---
    for worker_id, name, addr in master.list_workers():
        ip, port = addr
        add_worker_row(worker_id, name, ip, str(port))

    # --- poll for newly connected / externally removed workers ---
    # accept_workers() runs on its own thread with no GUI callback, so we
    # poll master.list_workers() periodically and diff against what the
    # table currently shows.
    def poll_workers():
        while True:
            time.sleep(1)
            current = master.list_workers()
            current_ids = {cid for cid, _, _ in current}
            known_ids = set(worker_order)
            new_ids = current_ids - known_ids
            gone_ids = known_ids - current_ids
            for cid, name, addr in current:
                if cid in new_ids:
                    ip, port = addr
                    page.run_thread(lambda cid=cid, name=name, ip=ip, port=port: (
                        add_worker_row(cid, name, ip, str(port)),
                        add_log_line(f"[{timestamp()}] Worker {cid} connected from {ip}:{port}"),
                    ))
            for cid in gone_ids:
                page.run_thread(lambda cid=cid: remove_worker_row(cid))

    threading.Thread(target=poll_workers, daemon=True).start()