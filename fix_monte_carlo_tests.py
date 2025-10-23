#!/usr/bin/env python3
"""
Script to fix Monte Carlo tests by adding proper authentication mocks.
"""

import re
import os

def fix_monte_carlo_test_file():
    """Fix the Monte Carlo test file by adding authentication mocks to all test methods."""
    
    file_path = "/Users/juliettecattin/WebstormProjects/high-performance-trading-platform/backend/api/tests/test_monte_carlo_sync.py"
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Pattern to match test methods that need authentication mocks
    test_method_pattern = r'(\s+)(def test_sync_monte_carlo_\w+)\(self\):'
    
    # Replacement with authentication mocks
    def add_auth_mocks(match):
        indent = match.group(1)
        method_signature = match.group(2)
        
        return f'''{indent}@patch("api.routes.monte_carlo.get_current_user_simple")
{indent}@patch("api.routes.monte_carlo.get_session")
{indent}{method_signature}(self, mock_get_session, mock_get_current_user, mock_simple_user, mock_jwt_token):'''
    
    # Apply the pattern replacement
    content = re.sub(test_method_pattern, add_auth_mocks, content)
    
    # Add authentication setup at the beginning of each test method
    auth_setup = '''        # Mock authentication
        mock_get_current_user.return_value = mock_simple_user
        
        # Mock database session
        mock_session = AsyncMock()
        mock_get_session.return_value = mock_session
        
        # Mock user repository
        with patch("api.routes.monte_carlo.UserRepository") as mock_user_repo_class:
            mock_user_repo = Mock()
            mock_user_repo.get_by_id = AsyncMock(return_value=Mock(id=1))
            mock_user_repo_class.return_value = mock_user_repo
            
            # Mock history repository
            with patch("api.routes.monte_carlo.BacktestHistoryRepository") as mock_history_repo_class:
                mock_history_repo = Mock()
                mock_history_entry = Mock(id=1)
                mock_history_repo.create_history_entry = AsyncMock(return_value=mock_history_entry)
                mock_history_repo.update_results = AsyncMock()
                mock_history_repo_class.return_value = mock_history_repo
                
'''
    
    # Pattern to find the start of test method bodies (after the docstring)
    method_body_pattern = r'(def test_sync_monte_carlo_\w+\([^)]+\):\s*"""[^"]*"""\s*)'
    
    def add_auth_setup_to_method(match):
        method_def = match.group(1)
        return method_def + auth_setup
    
    # Apply auth setup to methods
    content = re.sub(method_body_pattern, add_auth_setup_to_method, content, flags=re.DOTALL)
    
    # Fix client.post calls to include Authorization header
    post_pattern = r'(response = client\.post\(\s*"/api/v1/monte-carlo/run",\s*params=params)\)'
    post_replacement = r'\1,\n                    headers={"Authorization": f"Bearer {mock_jwt_token}"}\n                )'
    
    content = re.sub(post_pattern, post_replacement, content)
    
    # Indent all test content properly within the with blocks
    lines = content.split('\n')
    in_test_method = False
    in_auth_block = False
    new_lines = []
    
    for line in lines:
        if 'def test_sync_monte_carlo_' in line and 'mock_jwt_token' in line:
            in_test_method = True
            new_lines.append(line)
        elif in_test_method and line.strip().startswith('with patch("api.routes.monte_carlo.UserRepository")'):
            in_auth_block = True
            new_lines.append(line)
        elif in_test_method and in_auth_block and line.strip() and not line.startswith('        '):
            # Add proper indentation for content inside auth blocks
            if line.strip().startswith('params = {') or line.strip().startswith('response = ') or line.strip().startswith('assert '):
                new_lines.append('                ' + line.strip())
            else:
                new_lines.append(line)
        elif in_test_method and line.strip().startswith('def ') and 'test_sync_monte_carlo_' not in line:
            in_test_method = False
            in_auth_block = False
            new_lines.append(line)
        else:
            new_lines.append(line)
    
    content = '\n'.join(new_lines)
    
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"Fixed Monte Carlo test file: {file_path}")

if __name__ == "__main__":
    fix_monte_carlo_test_file()