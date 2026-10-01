import customtkinter as ctk
import threading
from main import process_nexus_turn, user_data

# 1. Design & Appearance-Einstellungen
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NexusApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Fenster-Konfiguration
        self.title("Projekt Nexus // Core Terminal")
        self.geometry("1050x720")
        self.minsize(800, 550)

        # Hauptlayout: 2 Spalten (Links: Sidebar, Rechts: Chat-Bereich)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=0) # Sidebar feste Breite
        self.grid_columnconfigure(1, weight=1) # Chat dehnt sich aus

        # --- SEITENLEISTE (Sidebar) ---
        self.sidebar = ctk.CTkFrame(self, width=240, fg_color="#18181b", corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        # Logo / Titel in Sidebar
        self.logo_label = ctk.CTkLabel(
            self.sidebar, 
            text="NEXUS // CORE", 
            font=("Segoe UI", 16, "bold"), 
            text_color="#ff5722"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 15), sticky="w")

        # Status Info Box
        self.status_box = ctk.CTkFrame(self.sidebar, fg_color="#222226", corner_radius=8)
        self.status_box.grid(row=1, column=0, padx=15, pady=10, sticky="ew")
        
        self.status_title = ctk.CTkLabel(self.status_box, text="SYSTEM STATUS", font=("Segoe UI", 10, "bold"), text_color="#888")
        self.status_title.pack(anchor="w", padx=12, pady=(8, 2))
        
        self.status_val = ctk.CTkLabel(self.status_box, text="● Online (Llama 3)", font=("Segoe UI", 12, "bold"), text_color="#4ade80")
        self.status_val.pack(anchor="w", padx=12, pady=(0, 8))

        # Schnell-Aktionen / Infos in der Sidebar
        self.info_label = ctk.CTkLabel(
            self.sidebar, 
            text="DIAGNOSE & TOOLS", 
            font=("Segoe UI", 11, "bold"), 
            text_color="#a1a1aa"
        )
        self.info_label.grid(row=2, column=0, padx=20, pady=(20, 5), sticky="w")

        self.btn_profile = ctk.CTkButton(
            self.sidebar, 
            text="Profil anzeigen", 
            fg_color="#27272a", 
            hover_color="#3f3f46", 
            text_color="#e4e4e7",
            font=("Segoe UI", 12),
            command=self.show_profile_info
        )
        self.btn_profile.grid(row=3, column=0, padx=15, pady=5, sticky="ew")

        self.btn_clear = ctk.CTkButton(
            self.sidebar, 
            text="Chat leeren", 
            fg_color="#27272a", 
            hover_color="#3f3f46", 
            text_color="#e4e4e7",
            font=("Segoe UI", 12),
            command=self.clear_chat
        )
        self.btn_clear.grid(row=4, column=0, padx=15, pady=5, sticky="ew")

        # Footer in Sidebar
        self.footer_label = ctk.CTkLabel(
            self.sidebar, 
            text="User: Ian\nModus: Unbarmherzig", 
            font=("Segoe UI", 11), 
            text_color="#71717a",
            justify="left"
        )
        self.footer_label.grid(row=6, column=0, padx=20, pady=20, sticky="sw")

        # --- HAUPTBEREICH (Chat-Fenster) ---
        self.chat_container = ctk.CTkFrame(self, fg_color="#121214", corner_radius=0)
        self.chat_container.grid(row=0, column=1, sticky="nsew")
        
        self.chat_container.grid_rowconfigure(0, weight=1)
        self.chat_container.grid_rowconfigure(1, weight=0)
        self.chat_container.grid_columnconfigure(0, weight=1)

        # Scrollbarer Chat-Verlauf
        self.chat_frame = ctk.CTkScrollableFrame(
            self.chat_container, 
            fg_color="#121214", 
            corner_radius=0
        )
        self.chat_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.chat_frame.grid_columnconfigure(0, weight=1)

        # Willkommensnachricht von Nexus
        self.add_message("Nexus", "System hochgefahren. Was gibt's, Ian? Hau raus.", align="left", bg_color="#1e1e24")

        # Eingabebereich unten
        self.input_container = ctk.CTkFrame(self.chat_container, fg_color="#18181b", height=80, corner_radius=0)
        self.input_container.grid(row=1, column=0, sticky="ew")
        self.input_container.grid_columnconfigure(0, weight=1)

        self.input_wrapper = ctk.CTkFrame(self.input_container, fg_color="transparent")
        self.input_wrapper.pack(fill="both", expand=True, padx=20, pady=15)
        self.input_wrapper.grid_columnconfigure(0, weight=1)

        # Textfeld mit lila Text und Hover-Effekt
        self.entry = ctk.CTkEntry(
            self.input_wrapper,
            placeholder_text="Schreib Nexus etwas...",
            height=48,
            corner_radius=24,
            border_width=1,
            border_color="#3f3f46",
            fg_color="#09090b",
            text_color="#c792ea",  # Textfarbe lila wie gewünscht
            font=("Segoe UI", 14)
        )
        self.entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entry.bind("<Return>", lambda event: self.send_message())
        
        # Hover-Effekte fürs Eingabefeld binden
        self.entry.bind("<Enter>", lambda e: self.entry.configure(border_color="#71717a"))
        self.entry.bind("<Leave>", lambda e: self.entry.configure(border_color="#3f3f46"))

        # Senden-Button mit Hover-Größeneffekt (über Farbwechsel/Hover-Color simuliert)
        self.send_button = ctk.CTkButton(
            self.input_wrapper,
            text="Senden",
            width=110,
            height=48,
            corner_radius=24,
            fg_color="#ff5722",
            hover_color="#f43f5e",
            font=("Segoe UI", 13, "bold"),
            command=self.send_message
        )
        self.send_button.grid(row=0, column=1)

    def add_message(self, sender: str, text: str, align: str, bg_color: str):
        """Erstellt eine Nachricht im Chat und scrollt vollautomatisch nach unten."""
        msg_box = ctk.CTkFrame(
            self.chat_frame, 
            fg_color=bg_color, 
            corner_radius=12
        )
        
        if align == "right":
            msg_box.grid(padx=(80, 20), pady=8, sticky="e")
        else:
            msg_box.grid(padx=(20, 80), pady=8, sticky="w")

        header_label = ctk.CTkLabel(
            msg_box, 
            text=sender, 
            font=("Segoe UI", 11, "bold"), 
            text_color="#a1a1aa"
        )
        header_label.pack(anchor="w", padx=14, pady=(8, 2))

        text_label = ctk.CTkLabel(
            msg_box, 
            text=text, 
            font=("Segoe UI", 13), 
            text_color="#f4f4f5", 
            wraplength=600, 
            justify="left"
        )
        text_label.pack(anchor="w", padx=14, pady=(0, 10))

        # Automatisches Runterscrollen erzwingen
        self.after(50, self._force_scroll_bottom)

    def _force_scroll_bottom(self):
        """Scrollt den Chat-Frame zuverlässig an das Ende."""
        try:
            self.chat_frame._parent_canvas.yview_moveto(1.0)
        except Exception:
            pass

    def send_message(self):
        user_text = self.entry.get().strip()
        if not user_text:
            return

        self.entry.delete(0, "end")
        self.add_message("Du", user_text, align="right", bg_color="#27272a")

        self.send_button.configure(state="disabled", text="Denkt...")

        # Asynchroner Aufruf, damit das UI nicht einfriert
        threading.Thread(target=self._get_nexus_response, args=(user_text,), daemon=True).start()

    def _get_nexus_response(self, user_text: str):
        reply = process_nexus_turn(user_text)
        self.after(0, self._update_ui_after_response, reply)

    def _update_ui_after_response(self, reply: str):
        self.add_message("Nexus", reply, align="left", bg_color="#1e1e24")
        self.send_button.configure(state="normal", text="Senden")

    def show_profile_info(self):
        """Zeigt kurz den Status der Updates aus dem Profil an."""
        updates = user_data.get("updates", [])
        count = len(updates)
        self.add_message("System", f"Profil-Info: {count} aktive Update-Einträge geladen.", align="left", bg_color="#222226")

    def clear_chat(self):
        """Entfernt alle Widgets im Chatfenster, um es aufzuräumen."""
        for widget in self.chat_frame.winfo_children():
            widget.destroy()
        self.add_message("Nexus", "Chat gereinigt. Was gibt's Neues?", align="left", bg_color="#1e1e24")

if __name__ == "__main__":
    app = NexusApp()
    app.mainloop()