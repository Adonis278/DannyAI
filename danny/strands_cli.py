"""
Danny AI - Strands Interactive CLI

Interactive command-line interface using the Strands agent framework.
"""

import os
import sys
import warnings

# Suppress Pydantic serialization warnings from Strands
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from dotenv import load_dotenv

load_dotenv()

console = Console()


def main():
    """Run the interactive Danny CLI."""
    console.print(Panel.fit(
        "[bold blue]🦷 Danny AI - Dental Assistant[/bold blue]\n"
        "[dim]Powered by Strands Agent Framework[/dim]",
        border_style="blue"
    ))
    
    console.print("\n[dim]Type 'quit' or 'exit' to end the conversation.[/dim]")
    console.print("[dim]Type 'reset' to start a new conversation.[/dim]\n")
    
    # Import and create agent
    try:
        from danny.strands_agent import create_danny_agent
        
        use_bedrock = os.getenv("USE_BEDROCK", "false").lower() == "true"
        if use_bedrock:
            console.print("[yellow]Using AWS Bedrock (Claude)[/yellow]")
        else:
            console.print("[green]Using Anthropic API (Claude)[/green]")
        
        # Use quiet=True to suppress tool call output
        agent = create_danny_agent(use_bedrock=use_bedrock, quiet=True)
        console.print(f"[dim]Agent: {agent.name}[/dim]\n")
        
    except Exception as e:
        console.print(f"[red]Error initializing agent: {e}[/red]")
        return
    
    # Initial greeting
    console.print("[bold cyan]Danny:[/bold cyan]")
    try:
        greeting = agent("A patient just called. Greet them warmly.")
        greeting_text = extract_response_text(greeting)
        console.print(Markdown(greeting_text))
    except Exception as e:
        console.print(f"Hello! I'm Danny, your AI dental assistant. How can I help you today?")
    
    console.print()
    
    # Conversation loop
    while True:
        try:
            user_input = console.input("[bold green]You:[/bold green] ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                console.print("\n[bold cyan]Danny:[/bold cyan] Thank you for calling! Have a great day! 👋")
                break
            
            if user_input.lower() == 'reset':
                agent = create_danny_agent(use_bedrock=use_bedrock, quiet=True)
                console.print("\n[yellow]Conversation reset.[/yellow]\n")
                continue
            
            # Get response from Danny
            console.print("\n[bold cyan]Danny:[/bold cyan]")
            
            response = agent(user_input)
            response_text = extract_response_text(response)
            
            # Check for transfer request
            if "[TRANSFER_REQUESTED]" in response_text:
                response_text = response_text.split("[TRANSFER_REQUESTED]")[0].strip()
                console.print(Markdown(response_text))
                console.print("\n[yellow]📞 Call would be transferred to staff.[/yellow]")
            else:
                console.print(Markdown(response_text))
            
            console.print()
            
        except KeyboardInterrupt:
            console.print("\n\n[bold cyan]Danny:[/bold cyan] Goodbye! 👋")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


def extract_response_text(response) -> str:
    """Extract text from Strands AgentResult."""
    if hasattr(response, 'message') and response.message:
        msg = response.message
        if isinstance(msg, dict):
            content = msg.get('content', [])
            if isinstance(content, list):
                texts = []
                for item in content:
                    if isinstance(item, dict) and 'text' in item:
                        texts.append(item['text'])
                return '\n'.join(texts)
            elif isinstance(content, str):
                return content
        elif hasattr(msg, 'content'):
            return str(msg.content)
        else:
            return str(msg)
    elif hasattr(response, 'content'):
        return str(response.content)
    else:
        text = str(response)
        # Clean up dict repr if needed
        if text.startswith("{'role':"):
            try:
                parsed = eval(text)
                content = parsed.get('content', [])
                if isinstance(content, list) and content:
                    return content[0].get('text', text)
            except:
                pass
        return text


if __name__ == "__main__":
    main()
