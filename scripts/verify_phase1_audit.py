
import sys
import os
from unittest.mock import MagicMock, patch

# Add src and backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../backend/agents")))

def test_audit_logger():
    print("Testing AuditLogger logic with early mocks...")
    
    # 1. Setup Mocks BEFORE imports
    mock_get_session = MagicMock()
    mock_session_manager_cls = MagicMock()
    
    # Mocking the session behavior
    mock_session = MagicMock()
    mock_get_session.return_value.__enter__.return_value = mock_session

    with patch('cdss.db.session.get_session', mock_get_session), \
         patch('shared.session_manager.SessionManager', mock_session_manager_cls):
        
        # 2. Import AuditLogger NOW (inside the patch context)
        # Note: we use direct import from the module to be safe
        from shared.audit_logger import AuditLogger
        
        mock_sm_instance = mock_session_manager_cls.return_value
        logger = AuditLogger(mock_sm_instance)
        
        # 3. Test log_action
        logger.log_action(
            user_id="DR-123",
            action="TEST_ACTION",
            resource_type="PATIENT",
            resource_id="P-456",
            session_id="SESS-789"
        )
        
        # 4. Verification
        # RDS check
        if mock_session.add.called:
            args, kwargs = mock_session.add.call_args
            audit_log_entry = args[0]
            print(f"RDS Audit Entry: {audit_log_entry.user_id}, {audit_log_entry.action}, {audit_log_entry.resource}")
            
            if audit_log_entry.action == "TEST_ACTION" and audit_log_entry.resource == "PATIENT:P-456":
                print("✅ RDS Audit entry looks correct")
            else:
                print("❌ RDS Audit entry is incorrect")
        else:
            print("❌ mock_session.add was NOT called")

        # SessionManager check
        if mock_sm_instance.add_message.called:
            print("✅ SessionManager.add_message was called")
        else:
            print("❌ SessionManager.add_message was NOT called")

if __name__ == "__main__":
    try:
        test_audit_logger()
    except Exception as e:
        print(f"❌ Test crashed: {e}")
        import traceback
        traceback.print_exc()
