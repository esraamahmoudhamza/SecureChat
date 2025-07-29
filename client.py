import customtkinter as ctk
import pygame

import socket
import threading
import json
from playsound import playsound
import os

from crypto_utils import generate_keys, encrypt_message, decrypt_message, serialize_public_key
from cryptography.hazmat.primitives import serialization

HOST = '127.0.0.1'
PORT = 65432

private_key, public_key = generate_keys()


class ChatClient(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        self.title("Secure Chat by EsraaCodes 💬")
        self.geometry("550x650")
        self.configure(fg_color="#121212")

        # ===== Header =====
        self.header = ctk.CTkLabel(self, text="🔐 Secure Chat", font=("Arial", 18, "bold"), text_color="#8e44ad")
        self.header.pack(pady=(10, 5))

        # ===== Scrollable Frame for Chat =====
        self.chat_frame = ctk.CTkScrollableFrame(self, width=520, height=460, fg_color="#121212")
        self.chat_frame.pack(pady=(0, 10))
        self.chat_frame.grid_columnconfigure(0, weight=1)
        self.chat_frame.grid_columnconfigure(1, weight=1)

        self.message_widgets = []

        # ===== Message Input & Send Button =====
        self.bottom_frame = ctk.CTkFrame(self, fg_color="#1e1e1e")
        self.bottom_frame.pack(fill='x', padx=10, pady=5)

        self.msg_entry = ctk.CTkEntry(self.bottom_frame, width=400, placeholder_text="Type your message...")
        self.msg_entry.pack(side='left', padx=(10, 5), pady=10)

        self.send_button = ctk.CTkButton(self.bottom_frame, text="Send", command=self.send_message, fg_color="#8e44ad", hover_color="#732d91")
        self.send_button.pack(side='left', padx=5, pady=10)

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client_socket.connect((HOST, PORT))

        serialized_pub = serialize_public_key(public_key)
        self.client_socket.send(serialized_pub.encode())

        self.clients_public_keys = {}

        self.running = True
        thread = threading.Thread(target=self.receive_messages)
        thread.daemon = True
        thread.start()

    def send_message(self):
        message = self.msg_entry.get()
        if message.strip() == "":
            return

        for addr, pub_key in self.clients_public_keys.items():
            try:
                encrypted_msg = encrypt_message(pub_key, message)
                self.client_socket.send(encrypted_msg)
                self.add_message_bubble(message, sender='me')
                self.play_send_sound()
            except Exception as e:
                self.add_message_bubble(f"Error sending to {addr}: {e}", sender='system')

        self.msg_entry.delete(0, 'end')

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(8192)
                if not data:
                    break

                try:
                    decrypted_msg = decrypt_message(private_key, data)
                    self.add_message_bubble(decrypted_msg, sender='other')
                except Exception:
                    try:
                        keys_dict = json.loads(data.decode())
                        self.update_clients_public_keys(keys_dict)
                    except:
                        pass
            except Exception as e:
                self.add_message_bubble(f"Error: {e}", sender='system')
                self.running = False
                break

    def update_clients_public_keys(self, keys_dict):
        self.clients_public_keys.clear()
        for addr, key_str in keys_dict.items():
            if addr != str(self.client_socket.getsockname()):
                pub_key = serialization.load_pem_public_key(key_str.encode())
                self.clients_public_keys[addr] = pub_key
        self.add_message_bubble("[Updated keys list]", sender='system')

    def add_message_bubble(self, text, sender='other'):
        color = "#2c2c2c"
        anchor = 'w'
        column = 0

        if sender == 'me':
            color = "#8e44ad"
            anchor = 'e'
            column = 1
        elif sender == 'system':
            color = "#1e1e1e"
            anchor = 'center'
            column = 0

        bubble = ctk.CTkFrame(self.chat_frame, fg_color=color, corner_radius=15)
        label = ctk.CTkLabel(bubble, text=text, text_color="#ffffff", font=("Arial", 13), wraplength=300, justify='left')
        label.pack(padx=10, pady=5)

        bubble.grid(row=len(self.message_widgets), column=column, sticky=anchor, padx=10, pady=5)
        self.message_widgets.append(bubble)

        self.chat_frame.update_idletasks()
        self.chat_frame._parent_canvas.yview_moveto(1.0)  # scroll to bottom


    def play_send_sound(self):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load("send_sound.mp3")
            pygame.mixer.music.play()
        except Exception as e:
            print("Error playing sound:", e)


    def on_closing(self):
        self.running = False
        self.client_socket.close()
        self.destroy()


if __name__ == "__main__":
    app = ChatClient()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
