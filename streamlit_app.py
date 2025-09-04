# Import python packages
import streamlit as st
from snowflake.snowpark.functions import col
import requests
import pandas as pd

# Write directly to the app
st.title(f":cup_with_straw: Customize your Smoothie :cup_with_straw:")
st.write(
    """Choose the fruits you want in your Custom Smoothie
    """
)

name_on_order = st.text_input("Name on Smoothie: ")
st.write("The Name on your smoothie will be: ", name_on_order)

cnx = st.connection("snowflake")
session = cnx.session()
my_dataframe = session.table("smoothies.public.fruit_options").select(col('FRUIT_NAME'), col('SEARCH_ON'))
pd_df = my_dataframe.to_pandas()

ingredients_list = st.multiselect(
    'Choose up to 5 ingredients: ', my_dataframe,
    max_selections=5
)

if ingredients_list:
    ingredients_string = ''
    
    for fruit_chosen in ingredients_list:
        # Fix 1: Add space between ingredients (this might be the issue)
        if ingredients_string:
            ingredients_string += ' '  # Add space between fruits
        ingredients_string += fruit_chosen
        
        # Fix: Add error handling for the search_on lookup
        try:
            search_on = pd_df.loc[pd_df['FRUIT_NAME'] == fruit_chosen, 'SEARCH_ON'].iloc[0]
            
            # Check if search_on is None or empty
            if search_on is None or pd.isna(search_on):
                st.warning(f"No search value found for {fruit_chosen}. Skipping nutrition info.")
                continue
                
        except IndexError:
            st.warning(f"No matching search value found for {fruit_chosen}. Skipping nutrition info.")
            continue
        
        st.subheader(fruit_chosen + ' Nutrition information')
        
        try:
            smoothiefroot_response = requests.get("https://my.smoothiefroot.com/api/fruit/" + str(search_on))
            
            if smoothiefroot_response.status_code == 200:
                sf_df = st.dataframe(data=smoothiefroot_response.json(), width='stretch')
            else:
                st.error(f"Could not fetch nutrition data for {fruit_chosen}")
                
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching nutrition data for {fruit_chosen}: {str(e)}")
    
    # DEBUG: Show what the ingredients string looks like
    st.write("DEBUG - Ingredients string:", repr(ingredients_string))
    st.write("DEBUG - Ingredients string length:", len(ingredients_string))
    
    # Test different formatting options
    test_formats = {
        "Current format": ingredients_string,
        "No spaces": ''.join(ingredients_list),
        "Space separated": ' '.join(ingredients_list),
        "Stripped": ingredients_string.strip(),
        "Uppercase": ingredients_string.upper(),
        "Lowercase": ingredients_string.lower()
    }
    
    for format_name, format_string in test_formats.items():
        st.write(f"DEBUG - {format_name}: '{format_string}' (length: {len(format_string)})")
    
    # Only proceed if we have ingredients and a name
    if ingredients_string.strip() and name_on_order.strip():
        # Try multiple format options to see which one produces the right hash
        st.write("**Testing different ingredient formats:**")
        
        for format_name, format_string in test_formats.items():
            test_stmt = f"SELECT HASH('{format_string}') AS hash_value"
            try:
                hash_result = session.sql(test_stmt).collect()
                hash_value = hash_result[0]['HASH_VALUE']
                st.write(f"{format_name}: `{format_string}` → Hash: `{hash_value}`")
                
                # Check if this matches any expected values
                expected_hashes = {
                    7976616299844859825: "Kevin's expected",
                    -6112358379204300652: "Divya's expected", 
                    10169248411318185535: "Xi's expected"
                }
                
                if hash_value in expected_hashes:
                    st.success(f"✅ MATCH! {format_name} produces {expected_hashes[hash_value]} hash!")
                    
            except Exception as e:
                st.error(f"Error testing {format_name}: {str(e)}")
        
        # Use the original format for now
        my_insert_stmt = """ insert into smoothies.public.orders(ingredients, name_on_order)
                values ('""" + ingredients_string.strip() + """', '""" + name_on_order + """')"""
        st.write("SQL Statement:", my_insert_stmt)
        
        time_to_insert = st.button('Submit Order')
        if time_to_insert:
            try:
                session.sql(my_insert_stmt).collect()
                st.success('Your Smoothie is ordered!, ' + name_on_order, icon="✅")
            except Exception as e:
                st.error(f"Error submitting order: {str(e)}")
    else:
        st.warning("Please select ingredients and enter a name before submitting.")
