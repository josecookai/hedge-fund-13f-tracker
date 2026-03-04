"""
Basic tests for 13F Tracker
"""
import pytest
import sys
from pathlib import Path

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from parse_13f import F13Parser, parse_13f_file


class TestF13Parser:
    """Test 13F XML Parser"""
    
    def test_parse_empty(self):
        """Test parsing empty XML"""
        parser = F13Parser()
        result = parser.parse_xml("<informationTable></informationTable>")
        assert result['total_positions'] == 0
        assert result['holdings'] == []
    
    def test_parse_valid_xml(self):
        """Test parsing valid 13F XML"""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
            <infoTable>
                <nameOfIssuer>NVIDIA Corp</nameOfIssuer>
                <cusip>67066G104</cusip>
                <value>450000</value>
                <sshPrnamt>1500000</sshPrnamt>
                <sshPrnamtType>SH</sshPrnamtType>
                <investmentDiscretion>SOLE</investmentDiscretion>
                <votingAuthority>
                    <Sole>1500000</Sole>
                    <Shared>0</Shared>
                    <None>0</None>
                </votingAuthority>
            </infoTable>
        </informationTable>'''
        
        parser = F13Parser()
        result = parser.parse_xml(xml_content)
        
        assert result['total_positions'] == 1
        assert result['holdings'][0]['company_name'] == 'NVIDIA Corp'
        assert result['holdings'][0]['cusip'] == '67066G104'
        assert result['holdings'][0]['shares'] == 1500000
        assert result['holdings'][0]['value'] == 450000000  # In thousands
    
    def test_parse_multiple_positions(self):
        """Test parsing multiple positions"""
        xml_content = '''<?xml version="1.0" encoding="UTF-8"?>
        <informationTable xmlns="http://www.sec.gov/edgar/document/thirteenf/informationtable">
            <infoTable>
                <nameOfIssuer>Company A</nameOfIssuer>
                <cusip>111111111</cusip>
                <value>100000</value>
                <sshPrnamt>1000</sshPrnamt>
            </infoTable>
            <infoTable>
                <nameOfIssuer>Company B</nameOfIssuer>
                <cusip>222222222</cusip>
                <value>200000</value>
                <sshPrnamt>2000</sshPrnamt>
            </infoTable>
        </informationTable>'''
        
        parser = F13Parser()
        result = parser.parse_xml(xml_content)
        
        assert result['total_positions'] == 2
        assert len(result['holdings']) == 2


class TestSchema:
    """Test database schema"""
    
    def test_schema_exists(self):
        """Test that schema.sql file exists"""
        schema_path = Path(__file__).parent.parent / 'data' / 'schema.sql'
        assert schema_path.exists()
        
        content = schema_path.read_text()
        assert 'CREATE TABLE IF NOT EXISTS funds' in content
        assert 'CREATE TABLE IF NOT EXISTS filings' in content
        assert 'CREATE TABLE IF NOT EXISTS positions' in content


class TestFundRegistry:
    """Test fund registry"""
    
    def test_registry_exists(self):
        """Test that fund registry exists"""
        registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
        assert registry_path.exists()
    
    def test_registry_has_verified_funds(self):
        """Test that registry has verified funds"""
        import json
        registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
        data = json.loads(registry_path.read_text())
        
        assert 'verified_funds' in data
        assert len(data['verified_funds']) >= 3
        
        # Check Atreides
        atreides = [f for f in data['verified_funds'] if f['id'] == 'atreides-management']
        assert len(atreides) == 1
        assert atreides[0]['cik'] == '0001736297'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
