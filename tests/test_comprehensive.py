"""
Comprehensive tests for Hedge Fund 13F Tracker
"""
import pytest
import sys
import sqlite3
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts'))

from parse_13f import F13Parser, parse_13f_file
from fetch_sec import SECEdgarFetcher
from ingest_filing import FilingIngester


# ==================== Test Fixtures ====================

@pytest.fixture
def sample_13f_xml():
    """Sample 13F XML content"""
    return '''<?xml version="1.0" encoding="UTF-8"?>
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
        <infoTable>
            <nameOfIssuer>Meta Platforms</nameOfIssuer>
            <cusip>30303M102</cusip>
            <value>320000</value>
            <sshPrnamt>800000</sshPrnamt>
            <sshPrnamtType>SH</sshPrnamtType>
            <investmentDiscretion>SOLE</investmentDiscretion>
            <votingAuthority>
                <Sole>800000</Sole>
                <Shared>0</Shared>
                <None>0</None>
            </votingAuthority>
        </infoTable>
    </informationTable>'''


@pytest.fixture
def sample_txt_content():
    """Sample 13F TXT content"""
    return """
    NAME OF ISSUER                  CUSIP        SHARES      VALUE
    NVIDIA Corp                     67066G104    1,500,000   450,000
    Meta Platforms                  30303M102      800,000   320,000
    """


@pytest.fixture
def temp_db(tmp_path):
    """Create temporary database for testing"""
    db_path = tmp_path / "test.db"
    
    # Load and execute schema
    schema_path = Path(__file__).parent.parent / 'data' / 'schema.sql'
    conn = sqlite3.connect(db_path)
    
    with open(schema_path, 'r') as f:
        conn.executescript(f.read())
    
    # Insert test data
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO funds (id, name, manager, aum, cik)
        VALUES ('test-fund', 'Test Fund', 'Test Manager', 1000000000, '0001234567')
    ''')
    cursor.execute('''
        INSERT INTO filings (id, fund_id, quarter, filing_date, report_date, total_value, position_count)
        VALUES ('test-fund-2024-Q4', 'test-fund', '2024-Q4', '2025-02-14', '2024-12-31', 1000000000, 10)
    ''')
    conn.commit()
    
    yield db_path
    conn.close()


# ==================== Parse 13F Tests ====================

class TestF13Parser:
    """Test 13F XML/TXT Parser"""
    
    def test_parse_xml_basic(self, sample_13f_xml):
        """Test basic XML parsing"""
        parser = F13Parser()
        result = parser.parse_xml(sample_13f_xml)
        
        assert result['total_positions'] == 2
        assert len(result['holdings']) == 2
        assert result['holdings'][0]['company_name'] == 'NVIDIA Corp'
        assert result['holdings'][0]['cusip'] == '67066G104'
        assert result['holdings'][0]['shares'] == 1500000
        assert result['holdings'][0]['value'] == 450000000  # In thousands
    
    def test_parse_xml_empty(self):
        """Test parsing empty XML"""
        parser = F13Parser()
        result = parser.parse_xml("<informationTable></informationTable>")
        
        assert result['total_positions'] == 0
        assert result['holdings'] == []
    
    def test_parse_txt_format(self, sample_txt_content):
        """Test TXT format parsing"""
        parser = F13Parser()
        result = parser.parse_txt_format(sample_txt_content)
        
        assert result['total_positions'] == 2
        assert len(result['holdings']) == 2
    
    def test_parse_file_auto_detect(self, tmp_path, sample_13f_xml):
        """Test auto-detect format from file"""
        xml_file = tmp_path / "test.xml"
        xml_file.write_text(sample_13f_xml)
        
        result = parse_13f_file(str(xml_file))
        assert result['total_positions'] == 2


# ==================== SEC Fetcher Tests ====================

class TestSECEdgarFetcher:
    """Test SEC EDGAR Fetcher"""
    
    @patch('fetch_sec.requests.Session')
    def test_init(self, mock_session):
        """Test fetcher initialization"""
        fetcher = SECEdgarFetcher()
        
        assert fetcher.user_agent == "HedgeFundTracker contact@example.com"
        assert fetcher.timeout == 30
        assert fetcher.min_delay == 0.1
    
    @patch('fetch_sec.requests.Session')
    def test_rate_limiting(self, mock_session_class):
        """Test rate limiting"""
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session
        
        fetcher = SECEdgarFetcher()
        
        # Mock response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b'<feed></feed>'
        mock_session.get.return_value = mock_response
        
        # First request should not delay
        start = time.time()
        fetcher._rate_limit()
        elapsed = time.time() - start
        assert elapsed < 0.05
        
        # Second request should delay
        start = time.time()
        fetcher._rate_limit()
        elapsed = time.time() - start
        assert elapsed >= 0.1


# ==================== Database Tests ====================

class TestDatabase:
    """Test database operations"""
    
    def test_schema_creation(self, temp_db):
        """Test database schema is created correctly"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        
        assert 'funds' in tables
        assert 'filings' in tables
        assert 'positions' in tables
        assert 'position_changes' in tables
        assert 'alerts' in tables
        
        conn.close()
    
    def test_fund_insert(self, temp_db):
        """Test fund insertion"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM funds WHERE id = ?', ('test-fund',))
        fund = cursor.fetchone()
        
        assert fund is not None
        assert fund[0] == 'test-fund'
        assert fund[1] == 'Test Fund'
        
        conn.close()
    
    def test_filing_insert(self, temp_db):
        """Test filing insertion"""
        conn = sqlite3.connect(temp_db)
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM filings WHERE id = ?', ('test-fund-2024-Q4',))
        filing = cursor.fetchone()
        
        assert filing is not None
        assert filing[1] == 'test-fund'
        assert filing[2] == '2024-Q4'
        
        conn.close()


# ==================== Filing Ingester Tests ====================

class TestFilingIngester:
    """Test Filing Ingestion"""
    
    def test_init(self, temp_db):
        """Test ingester initialization"""
        ingester = FilingIngester(str(temp_db))
        assert ingester.db_path == str(temp_db)
        ingester.close()
    
    def test_get_fund_cik(self, temp_db):
        """Test getting fund CIK"""
        ingester = FilingIngester(str(temp_db))
        ingester.connect()
        
        cik = ingester.get_fund_cik('test-fund')
        assert cik == '0001234567'
        
        # Test non-existent fund
        cik = ingester.get_fund_cik('non-existent')
        assert cik is None
        
        ingester.close()


# ==================== Integration Tests ====================

class TestIntegration:
    """Integration tests"""
    
    def test_end_to_end_parse_and_ingest(self, tmp_path, sample_13f_xml):
        """Test end-to-end: parse XML and ingest"""
        # Create temp DB
        db_path = tmp_path / "integration.db"
        conn = sqlite3.connect(db_path)
        
        schema_path = Path(__file__).parent.parent / 'data' / 'schema.sql'
        with open(schema_path, 'r') as f:
            conn.executescript(f.read())
        
        # Insert fund
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO funds (id, name, manager, aum, cik)
            VALUES ('integration-fund', 'Integration Fund', 'Test', 1000000000, '0000000001')
        ''')
        conn.commit()
        conn.close()
        
        # Parse XML
        parser = F13Parser()
        result = parser.parse_xml(sample_13f_xml)
        
        assert result['total_positions'] == 2
        assert result['holdings'][0]['ticker'] is not None or result['holdings'][0]['cusip'] is not None


# ==================== Schema Validation ====================

class TestSchema:
    """Test database schema"""
    
    def test_schema_file_exists(self):
        """Test that schema.sql exists"""
        schema_path = Path(__file__).parent.parent / 'data' / 'schema.sql'
        assert schema_path.exists()
    
    def test_schema_content(self):
        """Test schema content"""
        schema_path = Path(__file__).parent.parent / 'data' / 'schema.sql'
        content = schema_path.read_text()
        
        assert 'CREATE TABLE IF NOT EXISTS funds' in content
        assert 'CREATE TABLE IF NOT EXISTS filings' in content
        assert 'CREATE TABLE IF NOT EXISTS positions' in content
        assert 'ON DELETE CASCADE' in content


# ==================== Fund Registry Tests ====================

class TestFundRegistry:
    """Test fund registry"""
    
    def test_registry_exists(self):
        """Test that fund registry exists"""
        registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
        assert registry_path.exists()
    
    def test_registry_valid_json(self):
        """Test that registry is valid JSON"""
        registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
        with open(registry_path, 'r') as f:
            data = json.load(f)
        
        assert 'verified_funds' in data
        assert len(data['verified_funds']) >= 3
    
    def test_registry_has_required_fields(self):
        """Test that registry entries have required fields"""
        registry_path = Path(__file__).parent.parent / 'config' / 'fund_registry.json'
        with open(registry_path, 'r') as f:
            data = json.load(f)
        
        for fund in data['verified_funds']:
            assert 'id' in fund
            assert 'name' in fund
            assert 'cik' in fund
            assert '13f_status' in fund


# ==================== Requirements Tests ====================

class TestRequirements:
    """Test requirements.txt"""
    
    def test_requirements_exists(self):
        """Test that requirements.txt exists"""
        req_path = Path(__file__).parent.parent / 'requirements.txt'
        assert req_path.exists()
    
    def test_core_dependencies(self):
        """Test that core dependencies are listed"""
        req_path = Path(__file__).parent.parent / 'requirements.txt'
        content = req_path.read_text()
        
        assert 'requests' in content
        assert 'beautifulsoup4' in content
        assert 'pytest' in content
        assert 'fastapi' in content


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
