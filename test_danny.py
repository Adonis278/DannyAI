"""
Quick test script for Danny AI.
Run this to verify everything is working.
"""

import asyncio
from danny.config import get_config
from danny.tools import get_calendly_tool, get_insurance_tool


async def test_config():
    """Test configuration loading."""
    print("=" * 50)
    print("Testing Configuration")
    print("=" * 50)
    
    config = get_config()
    errors = config.validate()
    
    if errors:
        print("❌ Configuration errors:")
        for e in errors:
            print(f"   - {e}")
        return False
    
    print(f"✅ Practice: {config.practice.name}")
    print(f"✅ Claude API Key: {'Set' if config.claude.api_key else 'Missing'}")
    print(f"✅ Calendly API Key: {'Set' if config.calendly.api_key else 'Missing'}")
    print(f"✅ AWS Region: {config.aws.region}")
    print(f"✅ Use Bedrock: {config.aws.use_bedrock}")
    return True


async def test_calendly():
    """Test Calendly integration."""
    print("\n" + "=" * 50)
    print("Testing Calendly Integration")
    print("=" * 50)
    
    tool = get_calendly_tool()
    
    try:
        # List appointment types
        print("\n📅 Fetching appointment types...")
        result = await tool.list_appointment_types()
        print(result)
        return True
    except Exception as e:
        print(f"❌ Calendly error: {e}")
        return False


async def test_insurance():
    """Test insurance tool."""
    print("\n" + "=" * 50)
    print("Testing Insurance Tool (Mock)")
    print("=" * 50)
    
    tool = get_insurance_tool()
    
    try:
        # Check eligibility
        print("\n🏥 Checking Delta Dental eligibility...")
        result = await tool.check_eligibility(carrier_name="Delta Dental")
        print(result[:500] + "..." if len(result) > 500 else result)
        
        # Check procedure coverage
        print("\n💰 Checking crown coverage (D2750)...")
        result = await tool.get_procedure_coverage("D2750")
        print(result[:500] + "..." if len(result) > 500 else result)
        
        return True
    except Exception as e:
        print(f"❌ Insurance error: {e}")
        return False


async def test_agent():
    """Test the Danny agent with a simple message."""
    print("\n" + "=" * 50)
    print("Testing Danny Agent")
    print("=" * 50)
    
    from danny.agent import get_danny_agent
    
    agent = get_danny_agent()
    session_id = "test-session-001"
    
    try:
        # Start conversation
        print("\n🤖 Starting conversation...")
        greeting = await agent.start_conversation(session_id)
        print(f"Danny: {greeting}")
        
        # Send a test message
        print("\n👤 User: What types of appointments can I book?")
        response = await agent.process_message(session_id, "What types of appointments can I book?")
        print(f"\n🤖 Danny: {response}")
        
        return True
    except Exception as e:
        print(f"❌ Agent error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n🦷 Danny AI - System Test\n")
    
    results = {
        "config": await test_config(),
        "calendly": await test_calendly(),
        "insurance": await test_insurance(),
        "agent": await test_agent()
    }
    
    print("\n" + "=" * 50)
    print("Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + ("🎉 All tests passed!" if all_passed else "⚠️ Some tests failed."))
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
