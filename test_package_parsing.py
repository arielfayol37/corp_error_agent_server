#!/usr/bin/env python3
"""
Simple test script to verify package parsing functionality
"""

def parse_packages(packages):
    """
    Parse packages from either dict or list format
    Returns: dict of {package_name: version}
    """
    if not packages:
        return {}
    
    if isinstance(packages, dict):
        # Already in the right format
        return packages
    
    elif isinstance(packages, list):
        # Parse list format like ["build==1.2.2.post1", "certifi==2025.6.15", ...]
        parsed_packages = {}
        for pkg_spec in packages:
            if isinstance(pkg_spec, str) and '==' in pkg_spec:
                # Handle "package==version" format
                parts = pkg_spec.split('==', 1)
                if len(parts) == 2:
                    pkg_name, pkg_version = parts
                    parsed_packages[pkg_name] = pkg_version
            elif isinstance(pkg_spec, str) and '>=' in pkg_spec:
                # Handle "package>=version" format
                parts = pkg_spec.split('>=', 1)
                if len(parts) == 2:
                    pkg_name, pkg_version = parts
                    parsed_packages[pkg_name] = f">={pkg_version}"
            elif isinstance(pkg_spec, str) and '<=' in pkg_spec:
                # Handle "package<=version" format
                parts = pkg_spec.split('<=', 1)
                if len(parts) == 2:
                    pkg_name, pkg_version = parts
                    parsed_packages[pkg_name] = f"<={pkg_version}"
            elif isinstance(pkg_spec, str) and '>' in pkg_spec:
                # Handle "package>version" format
                parts = pkg_spec.split('>', 1)
                if len(parts) == 2:
                    pkg_name, pkg_version = parts
                    parsed_packages[pkg_name] = f">{pkg_version}"
            elif isinstance(pkg_spec, str) and '<' in pkg_spec:
                # Handle "package<version" format
                parts = pkg_spec.split('<', 1)
                if len(parts) == 2:
                    pkg_name, pkg_version = parts
                    parsed_packages[pkg_name] = f"<{pkg_version}"
            elif isinstance(pkg_spec, str):
                # Just package name without version
                parsed_packages[pkg_spec] = "unknown"
        
        return parsed_packages
    
    return {}

def test_package_parsing():
    """Test the package parsing functionality"""
    
    # Test dict format
    print("Testing dict format...")
    dict_packages = {
        "numpy": "1.19.0",
        "pandas": "1.3.0"
    }
    parsed = parse_packages(dict_packages)
    print(f"Input: {dict_packages}")
    print(f"Output: {parsed}")
    print(f"Match: {parsed == dict_packages}")
    print()
    
    # Test list format with ==
    print("Testing list format with ==...")
    list_packages = [
        "build==1.2.2.post1",
        "certifi==2025.6.15",
        "charset-normalizer==3.4.2",
        "click==8.2.1",
        "colorama==0.4.6",
        "corp_error_agent==0.2.0",
        "idna==3.10",
        "importlib_metadata==8.7.0",
        "numpy==2.2.6",
        "packaging==25.0",
        "pip==25.1.1",
        "platformdirs==4.3.8",
        "pyproject_hooks==1.2.0",
        "requests==2.32.4",
        "setuptools==57.4.0",
        "tomli==2.2.1",
        "urllib3==2.5.0",
        "zipp==3.23.0"
    ]
    parsed = parse_packages(list_packages)
    print(f"Input list length: {len(list_packages)}")
    print(f"Output dict length: {len(parsed)}")
    print(f"Sample outputs:")
    for i, (pkg, ver) in enumerate(list(parsed.items())[:5]):
        print(f"  {pkg}: {ver}")
    print(f"All parsed: {len(parsed) == len(list_packages)}")
    print()
    
    # Test list format with other operators
    print("Testing list format with operators...")
    list_packages_ops = [
        "numpy>=1.19.0",
        "pandas<=1.3.0",
        "requests>2.0.0",
        "urllib3<2.0.0"
    ]
    parsed = parse_packages(list_packages_ops)
    expected = {
        "numpy": ">=1.19.0",
        "pandas": "<=1.3.0",
        "requests": ">2.0.0",
        "urllib3": "<2.0.0"
    }
    print(f"Input: {list_packages_ops}")
    print(f"Output: {parsed}")
    print(f"Expected: {expected}")
    print(f"Match: {parsed == expected}")
    print()
    
    # Test empty/None cases
    print("Testing edge cases...")
    print(f"None -> {parse_packages(None)}")
    print(f"[] -> {parse_packages([])}")
    print(f"{{}} -> {parse_packages({})}")
    print()
    
    print("All tests completed!")

if __name__ == "__main__":
    test_package_parsing() 