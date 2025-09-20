#!/usr/bin/env python3
"""
San Antonio MUD Server
Basic telnet server that accepts connections on port 2323
"""

import socket
import threading
import sys
from database import MUDDatabase

class ClientSession:
    def __init__(self, socket, address):
        self.socket = socket
        self.address = address
        self.authenticated = False
        self.user_id = None
        self.username = None
        self.auth_state = 'welcome'  # welcome, login_username, login_password, signup_username, signup_password

class MUDServer:
    def __init__(self, host='0.0.0.0', port=2323):
        self.host = host
        self.port = port
        self.clients = []
        self.sessions = {}  # socket -> ClientSession
        self.running = False
        self.db = MUDDatabase()

    def start(self):
        """Start the MUD server"""
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True

            print(f"San Antonio MUD Server starting on {self.host}:{self.port}")
            print("Press Ctrl+C to stop the server")
            print("="*50)

            # Get and display local IP address
            try:
                import socket as sock
                hostname = sock.gethostname()
                local_ip = sock.gethostbyname(hostname)
                print(f"🌐 Server accessible at:")
                print(f"   Local:    telnet localhost {self.port}")
                print(f"             nc localhost {self.port}")
                print(f"   Network:  telnet {local_ip} {self.port}")
                print(f"             nc {local_ip} {self.port}")
            except:
                print(f"🌐 Server accessible at:")
                print(f"   Local:    telnet localhost {self.port}")
                print(f"             nc localhost {self.port}")

            print("="*50)

            while self.running:
                try:
                    client_socket, address = self.server_socket.accept()
                    print(f"New connection from {address}")

                    # Create a new thread for each client
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, address)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                except socket.error:
                    if self.running:
                        print("Error accepting connection")

        except KeyboardInterrupt:
            print("\nShutting down server...")
        except Exception as e:
            print(f"Server error: {e}")
        finally:
            self.stop()

    def handle_client(self, client_socket, address):
        """Handle individual client connection"""
        try:
            # Create session
            session = ClientSession(client_socket, address)
            self.clients.append(client_socket)
            self.sessions[client_socket] = session

            # Send welcome message
            self.send_welcome(session)

            while self.running:
                try:
                    # Receive data from client
                    data = client_socket.recv(1024).decode('utf-8').strip()

                    if not data:
                        break

                    print(f"Received from {address}: {data}")

                    # Handle based on authentication state
                    if not session.authenticated:
                        self.handle_auth(session, data)
                    else:
                        self.handle_game_command(session, data)

                except socket.error:
                    break

        except Exception as e:
            print(f"Error handling client {address}: {e}")
        finally:
            # Clean up
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            if client_socket in self.sessions:
                del self.sessions[client_socket]
            client_socket.close()
            print(f"Client {address} disconnected")

    def send_welcome(self, session):
        """Send welcome message to new client"""
        msg = "Welcome to the San Antonio MUD\n"
        msg += "Type 'login' to sign in or 'signup' to create a new account\n"
        msg += "> "
        session.socket.send(msg.encode('utf-8'))

    def handle_auth(self, session, data):
        """Handle authentication flow"""
        data = data.lower().strip()

        if session.auth_state == 'welcome':
            if data == 'login':
                session.auth_state = 'login_username'
                session.socket.send("Username: ".encode('utf-8'))
            elif data == 'signup':
                session.auth_state = 'signup_username'
                session.socket.send("Choose a username: ".encode('utf-8'))
            elif data == 'quit':
                session.socket.send("Goodbye!\n".encode('utf-8'))
                session.socket.close()
            else:
                msg = "Please type 'login', 'signup', or 'quit'\n> "
                session.socket.send(msg.encode('utf-8'))

        elif session.auth_state == 'login_username':
            session.temp_username = data
            session.auth_state = 'login_password'
            session.socket.send("Password: ".encode('utf-8'))

        elif session.auth_state == 'login_password':
            success, result = self.db.authenticate_user(session.temp_username, data)
            if success:
                session.authenticated = True
                session.user_id = result
                session.username = session.temp_username
                msg = f"Welcome back, {session.username}!\n"
                msg += "You are at The Alamo Plaza\n"
                msg += "Type 'help' to see available commands\n> "
                session.socket.send(msg.encode('utf-8'))
            else:
                msg = f"Login failed: {result}\n"
                msg += "Type 'login' to try again or 'signup' to create account\n> "
                session.socket.send(msg.encode('utf-8'))
                session.auth_state = 'welcome'

        elif session.auth_state == 'signup_username':
            session.temp_username = data
            session.auth_state = 'signup_password'
            session.socket.send("Choose a password: ".encode('utf-8'))

        elif session.auth_state == 'signup_password':
            success, message = self.db.create_user(session.temp_username, data)
            if success:
                msg = f"Account created! Welcome to the San Antonio MUD, {session.temp_username}!\n\n"
                msg += "=== WELCOME GUIDE ===\n"
                msg += "You're now in The Alamo Plaza. Here are some basic commands to get started:\n\n"
                msg += "🔍 Exploring:\n"
                msg += "  'look' - See your surroundings, exits, people, and items\n"
                msg += "  'n/s/e/w' - Move north/south/east/west\n"
                msg += "  'where' - Check your current location\n\n"
                msg += "💬 Communication:\n"
                msg += "  'say <message>' - Talk to people in the same room\n"
                msg += "  'shout <message>' - Send message to everyone in the world\n"
                msg += "  'who' - See who's online\n\n"
                msg += "🎒 Items:\n"
                msg += "  'get <item>' - Pick up items you find\n"
                msg += "  'drop <item>' - Drop items from your inventory\n"
                msg += "  'inventory' (or 'inv') - See what you're carrying\n\n"
                msg += "🗣️ NPCs:\n"
                msg += "  'talk <npc>' - Chat with characters (try keywords!)\n\n"
                msg += "❓ Need help? Type 'help' anytime!\n"
                msg += "==================\n\n"
                msg += "You appear at The Alamo Plaza\n> "
                session.socket.send(msg.encode('utf-8'))
                session.authenticated = True
                session.username = session.temp_username
                # Get the user ID
                auth_success, user_id = self.db.authenticate_user(session.temp_username, data)
                if auth_success:
                    session.user_id = user_id
            else:
                msg = f"Signup failed: {message}\n"
                msg += "Type 'signup' to try again or 'login' to sign in\n> "
                session.socket.send(msg.encode('utf-8'))
                session.auth_state = 'welcome'

    def handle_game_command(self, session, data):
        """Handle game commands for authenticated users"""
        command_parts = data.strip().split()
        if not command_parts:
            session.socket.send("> ".encode('utf-8'))
            return

        command = command_parts[0].lower()

        if command == 'quit':
            session.socket.send("Goodbye! Your progress has been saved.\n".encode('utf-8'))
            session.socket.close()
        elif command == 'help':
            self.send_help(session)
        elif command == 'who':
            self.handle_who(session)
        elif command == 'where':
            self.handle_where(session)
        elif command == 'look':
            self.handle_look(session)
        elif command in ['move', 'go'] and len(command_parts) > 1:
            self.handle_move(session, command_parts[1])
        elif command in ['n', 'north', 's', 'south', 'e', 'east', 'w', 'west']:
            self.handle_move(session, command)
        elif command == 'say' and len(command_parts) > 1:
            self.handle_say(session, ' '.join(command_parts[1:]))
        elif command == 'shout' and len(command_parts) > 1:
            self.handle_shout(session, ' '.join(command_parts[1:]))
        elif command == 'talk' and len(command_parts) > 1:
            npc_name = command_parts[1]
            keyword = ' '.join(command_parts[2:]) if len(command_parts) > 2 else 'default'
            self.handle_talk(session, npc_name, keyword)
        elif command == 'get' and len(command_parts) > 1:
            item_name = ' '.join(command_parts[1:])
            self.handle_get(session, item_name)
        elif command == 'drop' and len(command_parts) > 1:
            item_name = ' '.join(command_parts[1:])
            self.handle_drop(session, item_name)
        elif command in ['inventory', 'inv', 'i']:
            self.handle_inventory(session)
        else:
            if command in ['say', 'shout']:
                msg = f"Usage: {command} <message>\n> "
            elif command == 'talk':
                msg = "Usage: talk <npc_name> [keyword]\n> "
            elif command == 'get':
                msg = "Usage: get <item>\n> "
            elif command == 'drop':
                msg = "Usage: drop <item>\n> "
            else:
                msg = f"Unknown command: {data}\nType 'help' for available commands\n> "
            session.socket.send(msg.encode('utf-8'))

    def send_help(self, session):
        """Send help message"""
        help_msg = "=== SAN ANTONIO MUD COMMANDS ===\n\n"
        help_msg += "🔍 EXPLORING:\n"
        help_msg += "  look - Show room description, exits, people, and items\n"
        help_msg += "  move <direction> - Move to another room\n"
        help_msg += "  n/s/e/w - Quick movement (north/south/east/west)\n"
        help_msg += "  where - Show your current location\n\n"
        help_msg += "🎒 ITEMS:\n"
        help_msg += "  get <item> - Pick up an item from the room\n"
        help_msg += "  drop <item> - Drop an item from your inventory\n"
        help_msg += "  inventory (inv/i) - Show what you're carrying\n\n"
        help_msg += "🗣️ NPCs:\n"
        help_msg += "  talk <npc> [keyword] - Talk to NPCs (try: history, food, music)\n\n"
        help_msg += "💬 COMMUNICATION:\n"
        help_msg += "  say <message> - Talk to people in the same room\n"
        help_msg += "  shout <message> - Send message to all players\n"
        help_msg += "  who - Show online players\n\n"
        help_msg += "⚙️ SYSTEM:\n"
        help_msg += "  help - Show this help\n"
        help_msg += "  quit - Exit the MUD\n\n"
        help_msg += "💡 TIP: Most commands work with partial names!\n"
        help_msg += "    Example: 'get guitar' instead of 'get a tortoiseshell guitar pick'\n"
        help_msg += "===============================\n> "
        session.socket.send(help_msg.encode('utf-8'))

    def handle_who(self, session):
        """Handle who command"""
        online_users = [s.username for s in self.sessions.values() if s.authenticated]
        msg = f"Online players: {', '.join(online_users)}\n> "
        session.socket.send(msg.encode('utf-8'))

    def handle_where(self, session):
        """Handle where command"""
        user_info = self.db.get_user_info(session.user_id)
        if user_info:
            room = self.db.get_room(user_info['current_room'])
            if room:
                msg = f"You are at {room['name']}\n> "
            else:
                msg = "You are in an unknown location\n> "
        else:
            msg = "Unable to determine your location\n> "
        session.socket.send(msg.encode('utf-8'))

    def handle_look(self, session):
        """Handle look command"""
        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to look around\n> ".encode('utf-8'))
            return

        room = self.db.get_room(user_info['current_room'])
        if not room:
            session.socket.send("You are in a void...\n> ".encode('utf-8'))
            return

        # Build room description
        msg = f"{room['name']}\n"
        msg += f"{room['description']}\n"

        # Show exits
        if room['exits']:
            exits_list = list(room['exits'].keys())
            msg += f"Exits: {', '.join(exits_list)}\n"
        else:
            msg += "No obvious exits\n"

        # Show players in room
        players_here = self.db.get_users_in_room(user_info['current_room'])
        players_here = [p for p in players_here if p != session.username]  # Exclude self
        if players_here:
            msg += f"Players here: {', '.join(players_here)}\n"
        else:
            msg += "Players here: none\n"

        # Show NPCs in room
        npcs_here = self.db.get_npcs_in_room(user_info['current_room'])
        if npcs_here:
            msg += f"NPCs here:\n"
            for npc in npcs_here:
                msg += f"  {npc['name']} - {npc['description']}\n"
        else:
            msg += "NPCs here: none\n"

        # Show items in room
        items_here = self.db.get_items_in_room(user_info['current_room'])
        if items_here:
            msg += f"Items here:\n"
            for item in items_here:
                msg += f"  {item['name']} - {item['description']}\n"
        else:
            msg += "Items here: none\n"

        msg += "> "
        session.socket.send(msg.encode('utf-8'))

    def handle_move(self, session, direction):
        """Handle movement commands"""
        # Normalize direction
        direction_map = {
            'n': 'north', 'north': 'north',
            's': 'south', 'south': 'south',
            'e': 'east', 'east': 'east',
            'w': 'west', 'west': 'west'
        }

        direction = direction_map.get(direction.lower(), direction.lower())

        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to move\n> ".encode('utf-8'))
            return

        current_room = self.db.get_room(user_info['current_room'])
        if not current_room:
            session.socket.send("You are lost in the void\n> ".encode('utf-8'))
            return

        # Check if direction is valid
        if direction not in current_room['exits']:
            msg = f"You can't go {direction} from here.\n"
            if current_room['exits']:
                exits_list = list(current_room['exits'].keys())
                msg += f"Available exits: {', '.join(exits_list)}\n"
            msg += "> "
            session.socket.send(msg.encode('utf-8'))
            return

        # Move to new room
        new_room_id = current_room['exits'][direction]
        new_room = self.db.get_room(new_room_id)

        if not new_room:
            session.socket.send("That way leads nowhere\n> ".encode('utf-8'))
            return

        # Update user location
        success = self.db.update_user_room(session.user_id, new_room_id)
        if success:
            msg = f"You head {direction}.\n\n"
            msg += f"{new_room['name']}\n"
            msg += f"{new_room['description']}\n"

            # Show exits
            if new_room['exits']:
                exits_list = list(new_room['exits'].keys())
                msg += f"Exits: {', '.join(exits_list)}\n"
            else:
                msg += "No obvious exits\n"

            # Show players in new room
            players_here = self.db.get_users_in_room(new_room_id)
            players_here = [p for p in players_here if p != session.username]
            if players_here:
                msg += f"Players here: {', '.join(players_here)}\n"
            else:
                msg += "Players here: none\n"

            msg += "> "
            session.socket.send(msg.encode('utf-8'))
        else:
            session.socket.send("Something went wrong trying to move\n> ".encode('utf-8'))

    def handle_say(self, session, message):
        """Handle say command - send message to players in same room"""
        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to speak\n> ".encode('utf-8'))
            return

        current_room = user_info['current_room']

        # Format the message
        chat_msg = f"[Room] {session.username}: {message}\n"

        # Send to all players in the same room
        players_notified = 0
        for client_socket, other_session in self.sessions.items():
            if (other_session.authenticated and
                other_session.user_id != session.user_id):  # Don't send to self

                other_user_info = self.db.get_user_info(other_session.user_id)
                if (other_user_info and
                    other_user_info['current_room'] == current_room):

                    try:
                        other_session.socket.send(chat_msg.encode('utf-8'))
                        other_session.socket.send("> ".encode('utf-8'))
                        players_notified += 1
                    except:
                        # Handle broken connections
                        pass

        # Confirm to sender
        confirm_msg = f"[Room] {session.username}: {message}\n"
        if players_notified == 0:
            confirm_msg += "(No one else is here to hear you)\n"
        confirm_msg += "> "
        session.socket.send(confirm_msg.encode('utf-8'))

    def handle_shout(self, session, message):
        """Handle shout command - send message to all players in the world"""
        # Format the message
        chat_msg = f"[Global] {session.username}: {message}\n"

        # Send to all authenticated players
        players_notified = 0
        for client_socket, other_session in self.sessions.items():
            if other_session.authenticated:
                try:
                    other_session.socket.send(chat_msg.encode('utf-8'))
                    other_session.socket.send("> ".encode('utf-8'))
                    players_notified += 1
                except:
                    # Handle broken connections
                    pass

        # Don't send separate confirmation since sender also receives the global message

    def handle_talk(self, session, npc_name, keyword):
        """Handle talk command - interact with NPCs"""
        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to talk\n> ".encode('utf-8'))
            return

        # Get NPCs in current room
        npcs_here = self.db.get_npcs_in_room(user_info['current_room'])

        # Find the NPC by name (case insensitive, partial match)
        target_npc = None
        npc_name_lower = npc_name.lower()

        for npc in npcs_here:
            # Check if the input matches the NPC name (partial match)
            if (npc_name_lower in npc['name'].lower() or
                any(npc_name_lower in word.lower() for word in npc['name'].split())):
                target_npc = npc
                break

        if not target_npc:
            msg = f"There's no '{npc_name}' here to talk to.\n"
            if npcs_here:
                npc_names = [npc['name'] for npc in npcs_here]
                msg += f"Available NPCs: {', '.join(npc_names)}\n"
            msg += "> "
            session.socket.send(msg.encode('utf-8'))
            return

        # Find response for keyword
        responses = target_npc['responses']
        keyword_lower = keyword.lower()

        # Look for exact keyword match first
        response = None
        if keyword_lower in responses:
            response = responses[keyword_lower]
        else:
            # Look for partial keyword matches
            for key, value in responses.items():
                if keyword_lower in key.lower() or key.lower() in keyword_lower:
                    response = value
                    break

        # If no keyword match, use default
        if not response:
            response = responses.get('default', f"{target_npc['name']} doesn't understand what you're asking about.")

        # Format and send response
        msg = f"{target_npc['name']} says: \"{response}\"\n> "
        session.socket.send(msg.encode('utf-8'))

        # Let other players in the room see the conversation
        for client_socket, other_session in self.sessions.items():
            if (other_session.authenticated and
                other_session.user_id != session.user_id):  # Don't send to self

                other_user_info = self.db.get_user_info(other_session.user_id)
                if (other_user_info and
                    other_user_info['current_room'] == user_info['current_room']):

                    try:
                        observer_msg = f"{session.username} talks to {target_npc['name']} about {keyword}.\n"
                        observer_msg += f"{target_npc['name']} says: \"{response}\"\n"
                        other_session.socket.send(observer_msg.encode('utf-8'))
                        other_session.socket.send("> ".encode('utf-8'))
                    except:
                        pass

    def handle_get(self, session, item_name):
        """Handle get command - pick up items"""
        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to get item\n> ".encode('utf-8'))
            return

        # Get items in current room
        items_here = self.db.get_items_in_room(user_info['current_room'])

        # Find the item by name (case insensitive, partial match)
        target_item = None
        item_name_lower = item_name.lower()

        for item in items_here:
            # Check if the input matches the item name (partial match)
            if (item_name_lower in item['name'].lower() or
                any(item_name_lower in word.lower() for word in item['name'].split())):
                target_item = item
                break

        if not target_item:
            msg = f"There's no '{item_name}' here to get.\n"
            if items_here:
                item_names = [item['name'] for item in items_here]
                msg += f"Available items: {', '.join(item_names)}\n"
            msg += "> "
            session.socket.send(msg.encode('utf-8'))
            return

        # Move item to player's inventory
        success = self.db.move_item(target_item['id'], 'player', session.user_id)
        if success:
            msg = f"You get {target_item['name']}.\n> "
            session.socket.send(msg.encode('utf-8'))

            # Let other players see the action
            for client_socket, other_session in self.sessions.items():
                if (other_session.authenticated and
                    other_session.user_id != session.user_id):

                    other_user_info = self.db.get_user_info(other_session.user_id)
                    if (other_user_info and
                        other_user_info['current_room'] == user_info['current_room']):

                        try:
                            observer_msg = f"{session.username} gets {target_item['name']}.\n"
                            other_session.socket.send(observer_msg.encode('utf-8'))
                            other_session.socket.send("> ".encode('utf-8'))
                        except:
                            pass
        else:
            session.socket.send("You can't get that item\n> ".encode('utf-8'))

    def handle_drop(self, session, item_name):
        """Handle drop command - drop items from inventory"""
        user_info = self.db.get_user_info(session.user_id)
        if not user_info:
            session.socket.send("Unable to drop item\n> ".encode('utf-8'))
            return

        # Get items in player's inventory
        player_items = self.db.get_player_items(session.user_id)

        # Find the item by name (case insensitive, partial match)
        target_item = None
        item_name_lower = item_name.lower()

        for item in player_items:
            # Check if the input matches the item name (partial match)
            if (item_name_lower in item['name'].lower() or
                any(item_name_lower in word.lower() for word in item['name'].split())):
                target_item = item
                break

        if not target_item:
            msg = f"You don't have '{item_name}' to drop.\n"
            if player_items:
                item_names = [item['name'] for item in player_items]
                msg += f"You're carrying: {', '.join(item_names)}\n"
            else:
                msg += "You're not carrying anything.\n"
            msg += "> "
            session.socket.send(msg.encode('utf-8'))
            return

        # Move item to current room
        success = self.db.move_item(target_item['id'], 'room', user_info['current_room'])
        if success:
            msg = f"You drop {target_item['name']}.\n> "
            session.socket.send(msg.encode('utf-8'))

            # Let other players see the action
            for client_socket, other_session in self.sessions.items():
                if (other_session.authenticated and
                    other_session.user_id != session.user_id):

                    other_user_info = self.db.get_user_info(other_session.user_id)
                    if (other_user_info and
                        other_user_info['current_room'] == user_info['current_room']):

                        try:
                            observer_msg = f"{session.username} drops {target_item['name']}.\n"
                            other_session.socket.send(observer_msg.encode('utf-8'))
                            other_session.socket.send("> ".encode('utf-8'))
                        except:
                            pass
        else:
            session.socket.send("You can't drop that item\n> ".encode('utf-8'))

    def handle_inventory(self, session):
        """Handle inventory command - show what player is carrying"""
        player_items = self.db.get_player_items(session.user_id)

        if player_items:
            msg = "You are carrying:\n"
            for item in player_items:
                msg += f"  {item['name']} - {item['description']}\n"
        else:
            msg = "You're not carrying anything.\n"

        msg += "> "
        session.socket.send(msg.encode('utf-8'))

    def stop(self):
        """Stop the server"""
        self.running = False

        # Close all client connections
        for client in self.clients:
            try:
                client.close()
            except:
                pass

        # Close server socket
        try:
            self.server_socket.close()
        except:
            pass

        print("Server stopped")

def main():
    server = MUDServer()
    try:
        server.start()
    except Exception as e:
        print(f"Failed to start server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()