"""
Tests for the Mergington High School API
"""

import pytest
from fastapi.testclient import TestClient
import sys
import copy
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to initial state before each test"""
    original_activities = copy.deepcopy(activities)
    yield
    # Reset after test
    activities.clear()
    activities.update(original_activities)


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client, reset_activities):
        """Test that GET /activities returns all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Chess Club" in data
        assert "Programming Class" in data
        assert len(data) > 0
    
    def test_get_activities_has_required_fields(self, client, reset_activities):
        """Test that activities have required fields"""
        response = client.get("/activities")
        data = response.json()
        chess_club = data["Chess Club"]
        assert "description" in chess_club
        assert "schedule" in chess_club
        assert "max_participants" in chess_club
        assert "participants" in chess_club
        assert isinstance(chess_club["participants"], list)
    
    def test_get_activities_participants_is_list(self, client, reset_activities):
        """Test that participants is a list"""
        response = client.get("/activities")
        data = response.json()
        for activity_name, activity in data.items():
            assert isinstance(activity["participants"], list)


class TestSignup:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client, reset_activities):
        """Test successful signup"""
        response = client.post(
            "/activities/Chess Club/signup?email=test@example.com"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "test@example.com" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup adds participant to activity"""
        initial_count = len(activities["Chess Club"]["participants"])
        client.post("/activities/Chess Club/signup?email=newstudent@example.com")
        assert len(activities["Chess Club"]["participants"]) == initial_count + 1
        assert "newstudent@example.com" in activities["Chess Club"]["participants"]
    
    def test_signup_duplicate_student(self, client, reset_activities):
        """Test that duplicate signup returns error"""
        client.post("/activities/Chess Club/signup?email=test@example.com")
        response = client.post(
            "/activities/Chess Club/signup?email=test@example.com"
        )
        assert response.status_code == 400
        data = response.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_activity_not_found(self, client, reset_activities):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@example.com"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]
    
    def test_signup_already_registered_student(self, client, reset_activities):
        """Test that already registered students can't signup again"""
        response = client.post(
            "/activities/Chess Club/signup?email=michael@mergington.edu"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]


class TestUnregister:
    """Tests for DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_unregister_successful(self, client, reset_activities):
        """Test successful unregister"""
        # First add a student
        client.post("/activities/Chess Club/signup?email=temp@example.com")
        # Then remove them
        response = client.delete(
            "/activities/Chess Club/unregister?email=temp@example.com"
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister removes participant from activity"""
        client.post("/activities/Chess Club/signup?email=remove@example.com")
        assert "remove@example.com" in activities["Chess Club"]["participants"]
        
        client.delete("/activities/Chess Club/unregister?email=remove@example.com")
        assert "remove@example.com" not in activities["Chess Club"]["participants"]
    
    def test_unregister_student_not_registered(self, client, reset_activities):
        """Test unregister for student not in activity"""
        response = client.delete(
            "/activities/Chess Club/unregister?email=notregistered@example.com"
        )
        assert response.status_code == 400
        data = response.json()
        assert "not signed up" in data["detail"]
    
    def test_unregister_activity_not_found(self, client, reset_activities):
        """Test unregister for non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@example.com"
        )
        assert response.status_code == 404
        data = response.json()
        assert "Activity not found" in data["detail"]


class TestIntegration:
    """Integration tests for signup and unregister flow"""
    
    def test_signup_then_unregister_flow(self, client, reset_activities):
        """Test full signup and unregister flow"""
        email = "integration@example.com"
        activity = "Tennis Club"
        
        # Check initial state
        initial_count = len(activities[activity]["participants"])
        assert email not in activities[activity]["participants"]
        
        # Signup
        signup_response = client.post(
            f"/activities/{activity}/signup?email={email}"
        )
        assert signup_response.status_code == 200
        assert email in activities[activity]["participants"]
        assert len(activities[activity]["participants"]) == initial_count + 1
        
        # Unregister
        unregister_response = client.delete(
            f"/activities/{activity}/unregister?email={email}"
        )
        assert unregister_response.status_code == 200
        assert email not in activities[activity]["participants"]
        assert len(activities[activity]["participants"]) == initial_count
    
    def test_multiple_signups_and_unregisters(self, client, reset_activities):
        """Test multiple signup and unregister operations"""
        activity = "Basketball"
        emails = ["user1@example.com", "user2@example.com", "user3@example.com"]
        
        # Sign up all users
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are signed up
        for email in emails:
            assert email in activities[activity]["participants"]
        
        # Unregister some
        response = client.delete(
            f"/activities/{activity}/unregister?email={emails[0]}"
        )
        assert response.status_code == 200
        assert emails[0] not in activities[activity]["participants"]
        assert emails[1] in activities[activity]["participants"]
        assert emails[2] in activities[activity]["participants"]
