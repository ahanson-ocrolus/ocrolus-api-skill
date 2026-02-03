"""Tkinter GUI for Transfer Book Automation."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import keyring

from ocrolus_automations.automations.move_book import MoveBookResult, extract_docs_from_status, run_move_book
from ocrolus_automations.clients.ocrolus_client import OcrolusClient
from ocrolus_automations.config import OrgCredentials
from ocrolus_automations.log_config import setup_logging

APP_NAME = "Transfer Book Automation"


def _service_name() -> str:
    return APP_NAME


def _key(org: str, field: str) -> str:
    return f"{org.lower().strip()}.{field}"


def load_credential(org: str, field: str) -> str:
    return keyring.get_password(_service_name(), _key(org, field)) or ""


def save_credential(org: str, field: str, value: str) -> None:
    if not value:
        return
    keyring.set_password(_service_name(), _key(org, field), value)


def clear_credentials(orgs: list[str]) -> None:
    for org in orgs:
        for field in ("client_id", "client_secret"):
            try:
                keyring.delete_password(_service_name(), _key(org, field))
            except keyring.errors.PasswordDeleteError:
                continue


class TransferBookApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("640x520")
        self.root.minsize(640, 520)

        self._queue: queue.Queue = queue.Queue()
        self._build_ui()
        self._load_saved_credentials()
        self._poll_queue()

    def _build_ui(self) -> None:
        style = ttk.Style()
        if "clam" in style.theme_names():
            style.theme_use("clam")

        container = ttk.Frame(self.root, padding=16)
        container.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        form = ttk.Frame(container)
        form.grid(row=0, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        self.source_id_var = tk.StringVar()
        self.source_secret_var = tk.StringVar()
        self.target_id_var = tk.StringVar()
        self.target_secret_var = tk.StringVar()
        self.source_book_var = tk.StringVar()
        self.target_book_name_var = tk.StringVar()

        row = 0
        ttk.Label(form, text="Org 1 (Source Org)", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Client ID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_id_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1
        ttk.Label(form, text="Client Secret").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_secret_var, show="*").grid(
            row=row, column=1, sticky="ew", padx=(8, 0)
        )
        row += 1
        ttk.Label(form, text="Source Book UUID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.source_book_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        row += 1

        ttk.Label(form, text="Org 2 (Target Org)", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Client ID").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_id_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1
        ttk.Label(form, text="Client Secret").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_secret_var, show="*").grid(
            row=row, column=1, sticky="ew", padx=(8, 0)
        )
        row += 1

        ttk.Separator(form).grid(row=row, column=0, columnspan=2, sticky="ew", pady=12)
        row += 1

        ttk.Label(form, text="Transfer Details", font=("Helvetica", 12, "bold")).grid(
            row=row, column=0, columnspan=2, sticky="w", pady=(0, 6)
        )
        row += 1
        ttk.Label(form, text="Target Book Name").grid(row=row, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.target_book_name_var).grid(row=row, column=1, sticky="ew", padx=(8, 0))
        row += 1

        form.columnconfigure(1, weight=1)

        button_row = ttk.Frame(container)
        button_row.grid(row=1, column=0, sticky="ew", pady=(16, 8))
        button_row.columnconfigure(0, weight=1)

        self.run_button = ttk.Button(button_row, text="Run Transfer", command=self._on_run)
        self.run_button.grid(row=0, column=0, sticky="w")

        self.clear_button = ttk.Button(button_row, text="Clear Saved Credentials", command=self._on_clear_creds)
        self.clear_button.grid(row=0, column=1, sticky="e")

        self.status = tk.Text(container, height=8, wrap="word", state="disabled")
        self.status.grid(row=2, column=0, sticky="nsew")
        container.rowconfigure(2, weight=1)

    def _load_saved_credentials(self) -> None:
        self.source_id_var.set(load_credential("org1", "client_id"))
        self.source_secret_var.set(load_credential("org1", "client_secret"))
        self.target_id_var.set(load_credential("org2", "client_id"))
        self.target_secret_var.set(load_credential("org2", "client_secret"))

    def _on_clear_creds(self) -> None:
        ok = messagebox.askyesno(
            "Confirm Clear",
            "This will remove saved credentials for the Source and Target orgs. Continue?",
        )
        if not ok:
            return
        clear_credentials(["org1", "org2"])
        self._log("Cleared saved credentials for Source and Target orgs.")

    def _validate(self) -> tuple[bool, str]:
        fields = {
            "Source client ID": self.source_id_var.get().strip(),
            "Source client secret": self.source_secret_var.get().strip(),
            "Target client ID": self.target_id_var.get().strip(),
            "Target client secret": self.target_secret_var.get().strip(),
            "Source book UUID": self.source_book_var.get().strip(),
            "Target book name": self.target_book_name_var.get().strip(),
        }
        for name, value in fields.items():
            if not value:
                return False, f"{name} is required."
        return True, ""

    def _on_run(self) -> None:
        ok, msg = self._validate()
        if not ok:
            messagebox.showerror("Missing info", msg)
            return

        self._save_credentials()
        self.run_button.config(state="disabled")
        self.clear_button.config(state="disabled")
        self._log("Starting transfer...")

        thread = threading.Thread(target=self._run_worker, daemon=True)
        thread.start()

    def _save_credentials(self) -> None:
        save_credential("org1", "client_id", self.source_id_var.get().strip())
        save_credential("org1", "client_secret", self.source_secret_var.get().strip())
        save_credential("org2", "client_id", self.target_id_var.get().strip())
        save_credential("org2", "client_secret", self.target_secret_var.get().strip())

    def _run_worker(self) -> None:
        try:
            source_org = "org1"
            target_org = "org2"
            creds = {
                source_org: OrgCredentials(
                    client_id=self.source_id_var.get().strip(),
                    client_secret=self.source_secret_var.get().strip(),
                ),
                target_org: OrgCredentials(
                    client_id=self.target_id_var.get().strip(),
                    client_secret=self.target_secret_var.get().strip(),
                ),
            }
            client = OcrolusClient(org_credentials=creds)

            self._queue.put(("log", "Validating source credentials and fetching book status..."))
            client.get_token(source_org)
            status = client.get_book_status(self.source_book_var.get().strip(), source_org)
            payload = status.get("response", status) if isinstance(status, dict) else status
            docs = extract_docs_from_status(payload)
            doc_count = len(docs)

            confirm_event = threading.Event()
            confirm_state = {"ok": False}
            confirm_msg = (
                f"This will create a new book in the Target Org and upload {doc_count} documents.\n\n"
                f"Target book name: {self.target_book_name_var.get().strip()}\n\n"
                "Continue?"
            )
            self._queue.put(("confirm", confirm_msg, confirm_event, confirm_state))
            confirm_event.wait()
            if not confirm_state["ok"]:
                self._queue.put(("log", "Transfer canceled."))
                self._queue.put(("done", None))
                return

            self._queue.put(("log", "Starting transfer..."))
            result = run_move_book(
                source_book_uuid=self.source_book_var.get().strip(),
                target_book_name=self.target_book_name_var.get().strip(),
                org_source=source_org,
                org_target=target_org,
                client=client,
                return_result=True,
            )
            self._queue.put(("result", result))
        except Exception as exc:
            self._queue.put(("error", str(exc)))
        finally:
            self._queue.put(("done", None))

    def _poll_queue(self) -> None:
        try:
            while True:
                item = self._queue.get_nowait()
                self._handle_queue_item(item)
        except queue.Empty:
            pass
        self.root.after(100, self._poll_queue)

    def _handle_queue_item(self, item: tuple) -> None:
        kind = item[0]
        if kind == "log":
            self._log(item[1])
        elif kind == "confirm":
            _, message, event, state = item
            ok = messagebox.askokcancel("Confirm Transfer", message)
            state["ok"] = ok
            event.set()
        elif kind == "result":
            result: MoveBookResult = item[1]
            if result.success:
                self._log("Transfer complete.")
            else:
                message = "Transfer failed."
                if result.created_target_book and result.target_book_uuid:
                    message += (
                        f"\n\nA new target book was created (UUID: {result.target_book_uuid})."
                        " Please delete this book before re-running."
                    )
                if result.failures:
                    message += "\n\nFailures:\n" + "\n".join(result.failures[:10])
                    if len(result.failures) > 10:
                        message += f"\n...and {len(result.failures) - 10} more"
                messagebox.showerror("Transfer failed", message)
                self._log("Transfer failed. See error dialog for details.")
        elif kind == "error":
            messagebox.showerror("Error", item[1])
            self._log(f"Error: {item[1]}")
        elif kind == "done":
            self.run_button.config(state="normal")
            self.clear_button.config(state="normal")

    def _log(self, message: str) -> None:
        self.status.config(state="normal")
        self.status.insert("end", message + "\n")
        self.status.see("end")
        self.status.config(state="disabled")


def main() -> None:
    setup_logging()
    root = tk.Tk()
    TransferBookApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
