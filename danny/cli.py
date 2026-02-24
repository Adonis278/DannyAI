"""
Command Line Interface for Danny AI.
Allows testing the agent locally via text chat.
"""

import asyncio
import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.prompt import Prompt

from .agent import get_danny_agent
from .conversation_manager import get_conversation_manager
from .config import get_config


console = Console()


def print_banner():
    """Print the Danny AI banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════╗
    ║                                                           ║
    ║     🦷  DANNY AI - Dental Practice Concierge  🦷          ║
    ║                                                           ║
    ║         Your AI-Powered Dental Receptionist               ║
    ║                                                           ║
    ╚═══════════════════════════════════════════════════════════╝
    """
    console.print(banner, style="bold blue")


def print_help():
    """Print available commands."""
    help_text = """
**Available Commands:**
- Type your message to talk to Danny
- `quit` or `exit` - End the conversation
- `new` - Start a new conversation
- `history` - Show conversation history
- `help` - Show this help message

**Test Scenarios:**
- "I'd like to schedule a cleaning"
- "What appointment types do you have?"
- "Is my Delta Dental insurance active?"
- "How much does a crown cost with insurance?"
- "I need to speak to someone"
    """
    console.print(Markdown(help_text))


async def run_chat():
    """Run the interactive chat loop."""
    print_banner()
    
    config = get_config()
    errors = config.validate()
    
    if errors:
        console.print("[red]Configuration errors:[/red]")
        for error in errors:
            console.print(f"  - {error}", style="red")
        console.print("\n[yellow]Please check your .env file and try again.[/yellow]")
        return
    
    console.print(f"[green]✓ Connected to {config.practice.name}[/green]")
    console.print(f"[green]✓ Using Claude model: {config.claude.model}[/green]")
    console.print(f"[green]✓ Calendly integration ready[/green]")
    console.print()
    
    print_help()
    console.print()
    
    # Initialize agent and conversation manager
    agent = get_danny_agent()
    manager = get_conversation_manager()
    
    # Start a new session
    session_id = manager.create_session()
    
    # Get Danny's greeting
    greeting = await agent.start_conversation(session_id)
    console.print(Panel(greeting, title="🦷 Danny", border_style="blue"))
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                # End conversation
                context = agent.end_conversation(session_id)
                if context:
                    log_path = manager.log_conversation(context)
                    console.print(f"\n[dim]Conversation saved to: {log_path}[/dim]")
                
                console.print("\n[blue]Danny:[/blue] Thank you for calling! Have a great day! 👋")
                break
            
            elif user_input.lower() == 'new':
                # Start new conversation
                context = agent.end_conversation(session_id)
                if context:
                    manager.log_conversation(context)
                
                session_id = manager.create_session()
                greeting = await agent.start_conversation(session_id)
                console.print(Panel(greeting, title="🦷 Danny", border_style="blue"))
                continue
            
            elif user_input.lower() == 'history':
                # Show recent conversations
                logs = manager.list_recent_conversations(5)
                if logs:
                    console.print("\n[bold]Recent Conversations:[/bold]")
                    for log in logs:
                        console.print(f"  - {log['session_id'][:8]}... | {log['start_time']} | {log['message_count']} messages")
                else:
                    console.print("[dim]No previous conversations found.[/dim]")
                continue
            
            elif user_input.lower() == 'help':
                print_help()
                continue
            
            # Process the message through Danny
            console.print("\n[dim]Danny is thinking...[/dim]")
            
            response = await agent.process_message(session_id, user_input)
            
            # Display response
            console.print()
            console.print(Panel(
                Markdown(response),
                title="🦷 Danny",
                border_style="blue"
            ))
            
            # Check for transfer request
            if "[TRANSFER_REQUESTED]" in response:
                console.print("\n[yellow]📞 In production, this would transfer to a human agent.[/yellow]")
                
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Saving conversation...[/yellow]")
            context = agent.end_conversation(session_id)
            if context:
                manager.log_conversation(context)
            break
        except Exception as e:
            console.print(f"\n[red]Error: {str(e)}[/red]")
            console.print("[yellow]Please try again or type 'quit' to exit.[/yellow]")


def main():
    """Main entry point for the CLI."""
    try:
        asyncio.run(run_chat())
    except Exception as e:
        console.print(f"[red]Fatal error: {str(e)}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
