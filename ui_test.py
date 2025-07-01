import pytest
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

@pytest.fixture
def driver():
    driver = webdriver.Chrome()
    yield driver
    driver.quit()

def test_home_page_title(driver):
    driver.get('http://localhost:5000/')
    assert "Music Recommendation System" in driver.title  

@pytest.mark.parametrize("redirect_contains", [
    ("/dashboard")
])
def test_spotify_auth(driver, redirect_contains):
    driver.get('http://localhost:5000/')
    
    get_rec_link = WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.LINK_TEXT, "Get Recommendations"))
    )
    get_rec_link.click()

    
    WebDriverWait(driver, 120).until(EC.url_contains(redirect_contains))
    assert redirect_contains in driver.current_url

if __name__ == '__main__':
    import pytest
    pytest.main([__file__])