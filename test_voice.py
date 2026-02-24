"""
Test script for Danny AI voice services.
Tests Amazon Polly and Transcribe with your AWS credentials.
"""

import asyncio
import os
from pathlib import Path


async def test_polly():
    """Test Amazon Polly text-to-speech."""
    print("\n" + "=" * 50)
    print("Testing Amazon Polly (Text-to-Speech)")
    print("=" * 50)
    
    try:
        from danny.voice.polly_handler import get_polly_handler
        
        polly = get_polly_handler()
        
        # Test synthesizing speech
        test_text = "Hello! I'm Danny, your AI dental assistant. How can I help you today?"
        print(f"\n🔊 Synthesizing: '{test_text}'")
        
        audio = polly.synthesize_speech(test_text)
        
        # Save to file for verification
        output_dir = Path("data/audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / "danny_greeting.mp3"
        
        with open(output_file, "wb") as f:
            f.write(audio)
        
        print(f"✅ Audio saved to: {output_file}")
        print(f"   File size: {len(audio):,} bytes")
        print(f"   Voice: {polly.voice_id} ({polly.engine})")
        
        # Test Spanish voice
        print("\n🇪🇸 Testing Spanish voice...")
        polly.set_spanish_voice()
        spanish_text = "Hola! Soy Danny, su asistente dental. ¿En qué puedo ayudarle?"
        spanish_audio = polly.synthesize_speech(spanish_text)
        
        spanish_file = output_dir / "danny_greeting_spanish.mp3"
        with open(spanish_file, "wb") as f:
            f.write(spanish_audio)
        
        print(f"✅ Spanish audio saved to: {spanish_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Polly error: {e}")
        return False


async def test_transcribe():
    """Test Amazon Transcribe configuration."""
    print("\n" + "=" * 50)
    print("Testing Amazon Transcribe (Speech-to-Text)")
    print("=" * 50)
    
    try:
        from danny.voice.transcribe_handler import get_transcribe_handler
        
        transcribe = get_transcribe_handler()
        print(f"✅ Transcribe handler initialized")
        print(f"   Region: {transcribe.config.aws.region}")
        print(f"   Language: {transcribe.language_code}")
        print(f"   Sample rate: {transcribe.sample_rate} Hz")
        
        # Note: We can't fully test Transcribe without an S3 audio file
        print("\n📝 Note: Full Transcribe test requires an audio file in S3.")
        print("   For real-time streaming, we'll use Amazon Connect's native Transcribe integration.")
        
        return True
        
    except Exception as e:
        print(f"❌ Transcribe error: {e}")
        return False


async def test_connect():
    """Test Amazon Connect configuration."""
    print("\n" + "=" * 50)
    print("Testing Amazon Connect")
    print("=" * 50)
    
    try:
        from danny.voice.connect_handler import get_connect_handler
        
        connect = get_connect_handler()
        
        instance_id = os.getenv("CONNECT_INSTANCE_ID", "")
        if not instance_id or instance_id == "YOUR_INSTANCE_ID_HERE":
            print("⚠️  Connect instance ID not configured yet")
            print("   Please update CONNECT_INSTANCE_ID in .env")
            return True  # Not a failure, just not configured
        
        connect.set_instance_id(instance_id)
        
        # List phone numbers
        print(f"\n📞 Listing phone numbers for instance: {instance_id[:20]}...")
        numbers = connect.list_phone_numbers()
        
        if numbers:
            print(f"✅ Found {len(numbers)} phone number(s):")
            for num in numbers:
                print(f"   - {num.get('PhoneNumber', 'Unknown')}")
        else:
            print("⚠️  No phone numbers found")
        
        # List contact flows
        print(f"\n📋 Listing contact flows...")
        flows = connect.list_contact_flows()
        
        if flows:
            print(f"✅ Found {len(flows)} contact flow(s):")
            for flow in flows[:5]:  # Show first 5
                print(f"   - {flow.get('Name', 'Unknown')}")
        else:
            print("⚠️  No contact flows found (that's normal for new instances)")
        
        return True
        
    except Exception as e:
        print(f"❌ Connect error: {e}")
        return False


async def test_lambda_handler():
    """Test the Lambda handler locally."""
    print("\n" + "=" * 50)
    print("Testing Lambda Handler (Local)")
    print("=" * 50)
    
    try:
        from danny.lambda_handler import lambda_handler
        
        # Simulate a Connect event
        test_event = {
            "Details": {
                "ContactData": {
                    "ContactId": "test-contact-123",
                    "CustomerEndpoint": {
                        "Address": "+15551234567",
                        "Type": "TELEPHONE_NUMBER"
                    },
                    "InitialContactId": "test-contact-123",
                    "Attributes": {}
                },
                "Parameters": {
                    "customer_input": "I'd like to schedule an appointment for a cleaning"
                }
            },
            "Name": "ContactFlowEvent"
        }
        
        print(f"\n🤖 Simulating call with input: '{test_event['Details']['Parameters']['customer_input']}'")
        
        result = lambda_handler(test_event, None)
        
        print(f"\n✅ Lambda response:")
        print(f"   Danny says: {result.get('danny_response', 'No response')[:200]}...")
        print(f"   Transfer requested: {result.get('transfer_requested', 'false')}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda handler error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all voice tests."""
    print("\n🔊 Danny AI - Voice Services Test\n")
    
    results = {
        "polly": await test_polly(),
        "transcribe": await test_transcribe(),
        "connect": await test_connect(),
        "lambda": await test_lambda_handler()
    }
    
    print("\n" + "=" * 50)
    print("Voice Test Results Summary")
    print("=" * 50)
    
    all_passed = True
    for test, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {test}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        print("\n🎉 All voice services are ready!")
        print("\n📋 Next steps:")
        print("   1. Update CONNECT_INSTANCE_ID in .env")
        print("   2. Create a contact flow in Connect console")
        print("   3. Deploy Lambda function to AWS")
        print("   4. Associate phone number with contact flow")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return all_passed


if __name__ == "__main__":
    asyncio.run(main())
