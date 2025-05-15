from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import pandas as pd
import os
import time

options = Options()
# options.add_argument("--headless")  # Uncomment this to run without opening a window
driver = webdriver.Firefox(options=options)
wait = WebDriverWait(driver, 15)  # Increased timeout
url = "https://uksa.statisticsauthority.gov.uk/digitaleconomyact-research-statistics/" \
      "better-useofdata-for-research-information-for-researchers/" \
      "list-of-accredited-researchers-and-research-projects-under-the-research-strand-of-the-digital-economy-act/"

try:
    print("Navigating to page...")
    driver.get(url)
    
    # Wait for table to fully load
    print("Waiting for table to load...")
    wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
    
    # Scraping loop
    all_data = []
    page_num = 1
    max_pages = 116  # Based on "Showing 1 to 10 of 1,153 entries"
    
    while True:
        print(f"Scraping page {page_num}...")
        
        # Extract rows from current page
        rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
        print(f"Found {len(rows)} rows on this page")
        
        for row in rows:
            cols = [col.text.strip() for col in row.find_elements(By.TAG_NAME, "td")]
            if cols:
                all_data.append(cols)
        
        # Try to navigate to the next page using JavaScript
        try:
            # Try a few different approaches to click "next" or the next page number
            if page_num >= max_pages:
                print("Reached maximum number of pages.")
                break
                
            next_page_script = """
                // Try to find and click the next page link
                var nextLink = document.querySelector('a.next, a.paginate_button.next');
                if (nextLink) {
                    nextLink.click();
                    return true;
                }
                
                // Try to find and click the next page number
                var pageLinks = document.querySelectorAll('a.paginate_button, .pagination a, [data-dt-idx]');
                for (var i = 0; i < pageLinks.length; i++) {
                    if (pageLinks[i].textContent.trim() === '""" + str(page_num + 1) + """') {
                        pageLinks[i].click();
                        return true;
                    }
                }
                
                return false;
            """
            
            success = driver.execute_script(next_page_script)
            
            if success:
                page_num += 1
                print(f"Navigating to page {page_num}...")
                # Wait for the page to load
                time.sleep(2)
                # Wait for table to load again
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr")))
            else:
                print("Could not find next page link. Reached last page.")
                break
                
        except Exception as e:
            print(f"Error navigating to next page: {e}")
            # save what we have
            if page_num > 1:
                print("Saving data that was successfully scraped before error...")
                break
            else:
                raise  # Re-raise the exception if we couldn't even scrape the first page

    # Save the data 
    print(f"\nTotal rows scraped: {len(all_data)}")
    
    # Determine number of columns and set headers accordingly
    if all_data:
        num_cols = max(len(row) for row in all_data)
        default_columns = [
            "Project ID", "Title", "Researchers", "Legal Basis",
            "Datasets Used", "Secure Research Service", "Accreditation Date"
        ]
        
        # Add generic column names if we have more columns than expected
        if num_cols > len(default_columns):
            columns = default_columns + [f"Column {i+1}" for i in range(len(default_columns), num_cols)]
        else:
            columns = default_columns[:num_cols]
            
        # Ensure all rows have the same number of columns
        for row in all_data:
            if len(row) < num_cols:
                row.extend([''] * (num_cols - len(row)))
                
        os.makedirs("data", exist_ok=True)
        output_path = os.path.join("data", "dea_accredited_projects.csv")
        df = pd.DataFrame(all_data, columns=columns)
        df.to_csv(output_path, index=False)
        print(f"\n✅ Scraped {len(df)} rows. Saved to {output_path}")
    else:
        print("No data was scraped.")

except Exception as e:
    print(f"An error occurred: {e}")
    import traceback
    traceback.print_exc()

finally:
    print("Closing browser...")
    driver.quit()