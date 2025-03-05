# GUI pyqt5 libraries
from PyQt5.QtWidgets import QFileDialog, QDialog, QMessageBox, QApplication
from PyQt5 import QtCore, QtGui

# Libries for shape and geopackage creation
import geopandas as gpd

# Utilities libraries
import time
import os
import pandas as pd
import numpy as np
import cv2
from ultralytics import YOLO
from geopy.geocoders import Nominatim
import torch

# Google Street Maps libry
import requests

# *.py scripts with complex methods
from coordinates_window import PolygonSettingWindow
from method_window import InspectionSetting
from dl_prediction_models import predict_llrs_img, predict_material_img, predict_code_img
from dl_prediction_models import predict_occupancy_img, predict_block_position_img, predict_n_stories_img
from get_building_orientation import get_street_view_image , get_road_orientation
from bounding_box_manual import BoundingBoxWindow

class GUIMethods:
    def __init__(self, ui):
        self.ui = ui  # Link to the UI components
        # Initialize attributes to avoid AttributeError
        self.click_count = -1           # Building ID aux varible     
        self.start = True               # Building ID aux varible  
        self.data_building = None       # Building sample information
        self.data_ai = None             # AI inspection
        self.data_expo = None           # Classic exposure model inspection
        self.data_old = None            # Existing inspection swicth
        self.sw_insp = True             # Existing inspection swicth           
        self.save_id = True             # Existing inspection swicth
        
        
    ############ Folder Selection ################
    def select_folder(self):
        """Open a folder selection dialog and display the selected folder in a text output."""
        folder_path = QFileDialog.getExistingDirectory(None, "Select Folder")
        if folder_path:  # If a folder is selected
            self.ui.output_folder_value.setText(folder_path)
            
    ############ Emergent window for define the boundary using a coordinate file ################
    def open_emergent_window(self):
        """
        Open an emergent window for defining a boundary using user input.
    
        This method launches a dialog window (`PolygonSettingWindow`) that allows users to manually 
        define a boundary polygon and provide city and country information. If a project folder 
        is not selected, a warning message is displayed. Upon successful input, the city and country 
        values are updated in the UI.
    
        Args:
            None. The method relies on UI components and user interaction for input.
    
        Returns:
            None. Updates the `city_value` and `country_value` fields in the UI with the user-provided 
            city and country information.
    
        Effects:
            - Displays a warning message if no project folder is selected.
            - Opens a dialog window for user input.
            - Updates UI fields with the data entered in the dialog.
    
        Notes:
            - The dialog must return `QDialog.Accepted` for the changes to be applied.
            - Logs a message when the polygon is successfully defined.
        """
        try:
            # dialog = PolygonSettingWindow(parent=self.ui, main_window=self.ui)
            dialog = PolygonSettingWindow(parent=self.ui, main_window=self.ui, gui_methods=self)
        except:
            QMessageBox.warning(self.ui, "Inspection Method Error", "Please select inspection method.")
        
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            QMessageBox.warning(self.ui, "Project Error", "Please select project folder")
        else:
            if dialog.exec_() == QDialog.Accepted:
                self.n_images_local = int(dialog.n_image_local_value.currentText())


    ############ Inspection Method Selection ################
    def select_insp_method(self):
        """There are three options for make the inspection the user should select one. 
           Please refer to user manual"""
        dialog = InspectionSetting(parent=self.ui, main_window=self.ui)
        dialog.exec_()  # This will open the emergent window as a modal
        
    
    ############ Get city name using coordinates ################
    def get_city_name(self):
        """
        Get the city name for a given latitude and longitude using reverse geocoding.
        
        Args:
            lat (float): Latitude of the point.
            lon (float): Longitude of the point.
        
        Returns:
            str: The name of the city, including the country, or an error message.
        """
        lat = float(self.ui.lat_value.text())
        lon = float(self.ui.lon_value.text())
            
        geolocator = Nominatim(user_agent="city_name_locator")
        location = geolocator.reverse((lat, lon), exactly_one=True, language="en")
        
        if location and 'address' in location.raw:
            address = location.raw['address']
            self.city = address.get('city', address.get('town', address.get('village', 'Unknown')))
            self.country = address.get('country', 'Unknown')
            self.city_name_manual = self.city+"_"+self.country
            self.ui.city_value.setText(self.city) 
            self.ui.country_value.setText(self.country) 
            return (self.city , self.country)
        
        return "City not found"
     
        
    ############ Create building dataset for upload images from GSV ################ 
    def create_database(self):
        """
        Create a CSV dataset of building information for uploading images from Google Street View (GSV).
    
        This method extracts relevant data (ID, latitude, and longitude) from a GeoPackage file containing 
        building centroids and saves it to a CSV file. If the CSV file already exists, the method skips execution.
    
        Args:
            None. The method operates on instance attributes such as `city_method`, `country_method`, 
            and the output folder path provided in the UI.
    
        Returns:
            None. The filtered building dataset is saved as a CSV file in the specified output folder.
    
        Effects:
            - Filters the GeoDataFrame to retain only the `id`, `latitude`, and `longitude` columns.
            - Exports the filtered data to a CSV file.
    
        Notes:
            - Checks for the existence of the CSV file to avoid creating duplicate files.
            - The exported CSV can be used for further processing, such as batch uploading to GSV.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            self.city_method = self.ui.city_value.text()
            self.country_method = self.ui.country_value.text()
            
            if self.ui.insp_method == 0:
                # Input and output for the method
                centroid_file=self.ui.output_folder_value.text()+"/"+self.city_method+"_"+self.country_method+"_subset_centroids.gpkg"
                database_file=self.ui.output_folder_value.text()+"/"+self.city_method+"_"+self.country_method+"_building_info.csv"
                # Check if a database file exists
                if os.path.exists(database_file):
                    pass
                else:
                    # Load the GeoPackage
                    gdf = gpd.read_file(centroid_file)
                    # Filter columns
                    filtered_gdf = gdf[['id', 'latitude', 'longitude']]
                    # Export to CSV
                    filtered_gdf.to_csv(database_file, index=False)             
                    print("Filtered CSV exported successfully!")
                    
            elif self.ui.insp_method == 1:
                centroid_file = self.ui.output_folder_value.text()+"/"+self.ui.file_name+".gpkg"
                database_file = self.ui.output_folder_value.text()+"/"+self.ui.file_name+"_building_info.csv"
                # Check if a database file exists
                if os.path.exists(database_file):
                    pass
                else:
                    # Load the GeoPackage
                    gdf = gpd.read_file(centroid_file)
                    # Filter columns
                    filtered_gdf = gdf[['ID', 'latitude', 'longitude']]
                    # Export to CSV
                    filtered_gdf.to_csv(database_file, index=False)             
                    print("Filtered CSV exported successfully!")
            
            elif self.ui.insp_method == 2:  
                pass # There is already the information in the csv with building information
                
                    
            # Upload the create building info to get the size of the inspection dataset
            # Craete an empty dataframe with the exact size
            if self.data_building is None:
                # Load the footprint database
                try:
                    # Footprint_data = size of inspection dataset
                    if self.ui.insp_method == 0:
                        footprint_data = pd.read_csv(self.ui.output_folder_value.text()+"/"+self.city_method+"_"+
                                                 self.country_method+"_building_info.csv")
                    elif self.ui.insp_method == 1:
                        footprint_data = pd.read_csv(self.ui.output_folder_value.text()+"/"+self.ui.file_name+"_building_info.csv")
                    elif self.ui.insp_method == 2:
                        footprint_data = pd.read_csv(self.ui.file_local_csv)
                except:
                    pass
                
                # Define the column namesfor the inspection database
                column_names = ["ID", 
                                "Latitude", 
                                "Longitude",
                                "Country",
                                "City",
                                "LLRS Material",
                                "LLRS",
                                "Code Level",
                                "Number of Stories",
                                "Occupancy",
                                "Block Position",
                                "Image Quality",
                                "Taxonomy",
                                "Image filename or link"]
                
                # Create an empty DataFrame for number of footprint available
                try:
                    if  self.data_ai == None:
                        self.data_ai = pd.DataFrame(np.full((footprint_data.shape[0]*3, len(column_names)), None), columns=column_names)
                    if  self.data_expo == None:
                        self.data_expo = pd.DataFrame(np.full((footprint_data.shape[0], len(column_names)), None), columns=column_names)
                except:
                    pass
        
            
    ############ Create building dataset for upload images from GSV ################     
    def load_existing_insp(self):
        """
        Load existing inspection data from CSV files based on the selected inspection method.

        This method checks whether a project folder, country, and city name are defined before 
        attempting to load previously saved inspection data. It retrieves existing AI and 
        exposure model inspection records from CSV files and integrates them into the 
        current dataset.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Upload existing inspections
            if self.start == True:
                try:
                    if self.ui.insp_method == 0:
                        output_folder = self.ui.output_folder_value.text()
                        insp_path = f"{output_folder}/{self.city_method}_{self.country_method}"
                        # Upload the existing inspections for AI 
                        self.data_ai_existing = pd.read_csv(insp_path+"_AI_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_ai.iloc[:self.data_ai_existing.shape[0], :] = self.data_ai_existing.iloc[:self.data_ai_existing.shape[0], :]
                        # Upload the existing inspections for exposure model
                        self.data_expo_existing = pd.read_csv(insp_path+"_EXPO_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_expo.iloc[:self.data_expo_existing.shape[0], :] = self.data_expo_existing.iloc[:self.data_expo_existing.shape[0], :]
                
                        print("Upload existing data sucessfully")
                        self.data_old = "OK"  # THERE IS EXISTING DATA
                        self.start = False
                        
                    elif self.ui.insp_method == 1:
                        insp_path = self.ui.output_folder_value.text()+"/"+self.ui.file_name 
                        # Upload the existing inspections for AI 
                        self.data_ai_existing = pd.read_csv(insp_path+"_AI_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_ai.iloc[:self.data_ai_existing.shape[0], :] = self.data_ai_existing.iloc[:self.data_ai_existing.shape[0], :]
                        # Upload the existing inspections for exposure model
                        self.data_expo_existing = pd.read_csv(insp_path+"_EXPO_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_expo.iloc[:self.data_expo_existing.shape[0], :] = self.data_expo_existing.iloc[:self.data_expo_existing.shape[0], :]
                
                        print("Upload existing data sucessfully")
                        self.data_old = "OK"  # THERE IS EXISTING DATA
                        self.start = False
                        
                    elif self.ui.insp_method == 2:
                        insp_path = self.ui.output_folder_value.text()+"/"+self.ui.file_name_local 
                        # Upload the existing inspections for AI 
                        self.data_ai_existing = pd.read_csv(insp_path+"_AI_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_ai.iloc[:self.data_ai_existing.shape[0], :] = self.data_ai_existing.iloc[:self.data_ai_existing.shape[0], :]
                        # Upload the existing inspections for exposure model
                        self.data_expo_existing = pd.read_csv(insp_path+"_EXPO_inspections.csv")
                        # Replace empty rows with the existing information
                        self.data_expo.iloc[:self.data_expo_existing.shape[0], :] = self.data_expo_existing.iloc[:self.data_expo_existing.shape[0], :]
                        
                        print("Upload existing data sucessfully")
                        self.data_old = "OK"  # THERE IS EXISTING DATA
                        self.start = False
                except:
                    pass

        
    ############ Counts the number of clicks made on the next button ################ 
    def count_clicks_next(self):
        """
        Increment the click counter and update the inspection dataset.
    
        This method increments the click counter to navigate through building inspections. 
        It ensures that a project folder, country, and city name are defined before execution. 
        If necessary, it loads the subset of buildings from a CSV file based on the selected 
        inspection method. The method also verifies that the current building ID does not 
        exceed the number of available samples.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            """Increment the click counter and update the label."""
            # load the dataset of the subset buildings
            if self.data_building is None:
                
                if self.ui.insp_method == 0:
                    path=self.ui.output_folder_value.text()+"/"+self.city_method+"_"+self.country_method+"_building_info.csv"
                    self.data_building = pd.read_csv(path)
                elif self.ui.insp_method == 1:
                    path= self.ui.output_folder_value.text()+"/"+self.ui.file_name+"_building_info.csv"
                    self.data_building = pd.read_csv(path)
                elif self.ui.insp_method == 2:
                    self.data_building = pd.read_csv(self.ui.file_local_csv)
                    
            # Verify that the building ID is less than the number of sample
            if self.click_count >= self.data_building.shape[0] - 1:
                # self.cont =  self.cont - 2
                QMessageBox.warning(self.ui, "Database Error", "No further inspections are available")
            else:
                self.ui.method_progress.setText("Loading images ...")
                
                # # Save inspection for first click after save results or start the script               
                if self.click_count >= 0:
                    self.inspection_database()
                
                # Check if there is inspection already done
                if self.data_old is not None:
                    self.n_insp = int(self.data_ai.dropna(how='all').shape[0])
                    self.data_old = None  # Only give the number of inspection one time per saved button clicked
                
                # Calculates the number of inspections saved
                try:
                    # Conditional for only update the number of click and the ID cont one time
                    if self.n_insp > 0 and self.sw_insp == True:
                        self.click_count = int(self.n_insp/3 - 1)
                        self.sw_insp = False
                except:
                    pass
                # ID increaser
                self.click_count += 1
                
        
    ############ Counts the number of clicks made on the previous button ################ 
    def count_clicks_previous(self):
        """
        Decrement the click counter to navigate to the previous building inspection.
    
        This method decreases the click counter, allowing the user to move back to a 
        previous inspection record. It ensures that a project folder, country, and 
        city name are defined before execution. If the dataset has not been initialized, 
        it prompts the user to click the "Next" button first.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            QMessageBox.warning(self.ui, "Project Error", "Please select project folder")
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            QMessageBox.warning(self.ui, "Country Error", "Please sets country name")
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            QMessageBox.warning(self.ui, "City Error", "Please sets city name")
        else:
            try:
                if self.data_building == None:
                    QMessageBox.warning(self.ui, "GUI Error", "Please click the Next button to start the GUI")
                else:
                    """Increment the click counter and update the label."""
                    if self.click_count > 0:
                        self.click_count += -1
                    else:
                        pass
            except:
                """Increment the click counter and update the label."""
                if self.click_count > 0:
                    self.click_count += -1
                else:
                    pass
        

    ############ Sets the coordinates of the building ################ 
    def coordinates(self):
        """
        Retrieve and update the building's coordinates in the User Interface (UI).
    
        This method fetches the latitude and longitude of the currently selected 
        building and updates the corresponding UI fields. It ensures that a project 
        folder, country, and city name are defined before execution. Additionally, 
        if the inspection method involves a polygon-based or specific method 
        (`insp_method` 1 or 2), it retrieves the city name dynamically.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Sets the coordinates of the building
            self.ui.lat_value.setText(str(round(self.data_building.iloc[self.click_count, 1],8)))
            self.ui.lon_value.setText(str(round(self.data_building.iloc[self.click_count, 2],8)))
        
        # Getting the city name for a Polygon method, where buildings could be located in different cities or countries.
        if self.ui.insp_method == 1:
            self.get_city_name()
        # Getting the city name for a specific method, where buildings could be located in different cities or countries.
        elif self.ui.insp_method == 2:
            self.get_city_name()
 
    ############ Checks if there is GSV availability ################  
    def check_street_view(self):
        """
        Check if Google Street View is available at the building's location.
    
        This method sends a request to the Google Street View API to determine 
        whether Street View imagery is available for the latitude and longitude 
        of the currently selected building. It ensures that a project folder, 
        country, and city name are defined before execution.
    
        Returns:
            bool: 
                - `True` if Street View imagery is available at the given location.
                - `False` if no Street View coverage exists.
    
        Effects:
            - Sends an HTTP request to the Google Street View API.
            - Retrieves metadata about Street View availability.
    
        Notes:
            - Requires a valid Google Street View API key.
            - The API key used in this function is hardcoded, which may pose security risks.
            - Ensures execution only if project details are correctly set.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Input parameters
            api_key = "AIzaSyBMINy7oPRKyOPW-wnZqQClXSUs11I9RBs"
            lat= self.ui.lat_value.text()
            lon= self.ui.lon_value.text() 
            url = "https://maps.googleapis.com/maps/api/streetview/metadata"
            params = {
                "location": f"{lat},{lon}",
                "key": api_key
            }
            response = requests.get(url, params=params)
            data = response.json()
            # Check status
            if data.get("status") == "OK":
                return True  # Street View is available
            else:
                return False  # No Street View coverage
        
            
    ############# Downnload GSV building images ################   
    def fetch_three_step_views(self):
        """
        Get in memory three directional Google Street View (GSV) images for a building's location.
    
        This method retrieves the latitude and longitude of a building, fetches three images from 
        Google Street View at angles of -30°, 0°, and +30°, and keep them in memory. The method updates 
        the UI with the image IDs for the current building. 
        If images already exist, it skips them.
    
        Args:
            None. The method relies on instance attributes such as `city_method`, `country_method`, 
            `data_building`, and UI elements for user input and display.
    
        Effects:
            - Fetches images from Google Street View using the provided API key.
            - Updates UI fields with image IDs.
    
        Notes:
            - Requires a valid Google Street View API key to fetch images.
            - Checks for Street View availability before attempting to fetch images.
            - Skips execution if no project folder is defined or if images already exist.
        """
             
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:

            # Building coordinates
            location = (float(self.ui.lat_value.text()), float(self.ui.lon_value.text()))
            # API key is required; without it, access to GSV is not possible
            api_key = "AIzaSyBMINy7oPRKyOPW-wnZqQClXSUs11I9RBs"  
            
            # Image ID displayed values
            # left image
            self.ui.img_id_value_1.setText(str(self.click_count+1)+"_1")
            # central image
            self.ui.img_id_value_2.setText(str(self.click_count+1)+"_2")
            # right image
            self.ui.img_id_value_3.setText(str(self.click_count+1)+"_3")
            
            if self.ui.insp_method != 2:                      
                # angles for taking the images
                angle = (-30,0,30)
                self.img_url = ["","",""]
                # img_frames = [self.ui.left_gsv_img,self.ui.central_gsv_img,self.ui.right_gsv_img]
                for aux in range (3):
                    if self.check_street_view() == True:
                        # Get image from GSV
                        self.img_url[aux] = get_street_view_image(location, api_key, angle[aux])[0]
                        if aux == 0:
                            self.img_orginial_1 = get_street_view_image(location, api_key, angle[aux])[1]
                        elif aux == 1:
                            self.img_orginial_2 = get_street_view_image(location, api_key, angle[aux])[1]
                        else:
                            self.img_orginial_3 = get_street_view_image(location, api_key, angle[aux])[1]
                    else:
                        print("Street View not available")
            else:
                pass

        
        
    ############ Building detector model ################
    def object_detector_building(self):
        """
        Detect and isolate buildings from Google Street View (GSV) images using a YOLO-based object detector.
        
        This method processes three directional GSV images (-30°, 0°, +30°) for a building's location and 
        applies a YOLO-based object detection model to identify and isolate buildings. The detected building 
        with the highest confidence is cropped and displayed in the User Interface. If no building is detected, a message 
        is displayed instead. The method handles images both in memory and from the local device.
        
        Args:
            None. The method relies on instance attributes such as `ui` for image display elements, 
            `img_orginial_1`, `img_orginial_2`, `img_orginial_3` for input images, and `data_building` 
            for project-specific data.
        
        Effects:
            - Loads a YOLO model for building detection.
            - Fetches and processes GSV images.
            - Identifies the most confident bounding box for buildings.
            - Crops and displays detected buildings in the UI.
            - Handles scenarios where no buildings are detected or Street View is unavailable.
        
        Notes:
            - Requires a trained YOLO model and corresponding weight file (`building_detector.pt`).
            - Checks if Street View coverage is available before performing detection.
        """
        # Class mapping (update this with your actual mappings)
        class_map = {0: "building-xzyh"}  # Replace with the correct mapping
        weight_path = "building_detector.pt" # Replace with your YOLO .pt file
        # Load the YOLO model
        model = YOLO(weight_path)
        # Set device GPU or CPU
        device= "cuda" if torch.cuda.is_available() else "cpu"
        model.to(device)
        # List of the frame
        img_frames = [self.ui.left_gsv_img,self.ui.central_gsv_img,self.ui.right_gsv_img]
        sw = True
        #Check inspection mode
        if self.ui.insp_method !=2:
            # Getting the images from GSV
            org_img = [self.img_orginial_1,self.img_orginial_2,self.img_orginial_3]
            # Vector for check if the building is detected
            self.predicted_img = [0,0,0]
            # Check GSV availability
            if self.check_street_view() == True:
                for aux in range (3):
                    if sw == True:
                        for i in range (100):
                            time.sleep(0.0001)
                            self.ui.progress_bar_method.setValue(i)
                            self.ui.method_progress.setText("Isolating building ....")
                        sw = False
            
                    # Ensure the image is in RGB format
                    image_rgb = org_img[aux]
            
                    # Run inference
                    results = model.predict(image_rgb)
            
                    highest_conf = 0
                    highest_conf_box = None
            
                    # Process the results
                    for result in results:
                        boxes = result.boxes.xyxy.cpu().numpy()  # Bounding box coordinates
                        confs = result.boxes.conf.cpu().numpy()  # Confidence scores
                        classes = result.boxes.cls.cpu().numpy()  # Class IDs
            
                        for box, conf, cls in zip(boxes, confs, classes):
                            cls = int(cls)
                            # Getting the building image with higher confidence as selected bounding box
                            if class_map.get(cls) == "building-xzyh" and conf > highest_conf:
                                highest_conf = conf
                                highest_conf_box = box
                    
                    # Create image for cropped and displayed
                    self.cropped_image = None
                    display_image = org_img[aux].copy()
                    
                    # Extracting selecting bounding box coordinates witin the image
                    if highest_conf_box is not None:
                        x1, y1, x2, y2 = map(int, highest_conf_box)
            
                        # Crop the area within the selected bounding box
                        self.cropped_image = org_img[aux][y1:y2, x1:x2]
            
                        # Draw a dashed rectangle for the highest confidence box
                        for i in range(x1, x2, 14):
                            cv2.line(display_image, (i, y1), (min(i + 5, x2), y1), (0, 0, 255), 3)
                            cv2.line(display_image, (i, y2), (min(i + 5, x2), y2), (0, 0, 255), 3)
                        for i in range(y1, y2, 14):
                            cv2.line(display_image, (x1, i), (x1, min(i + 5, y2)), (0, 0, 255), 3)
                            cv2.line(display_image, (x2, i), (x2, min(i + 5, y2)), (0, 0, 255), 3)
                            
                        if display_image is not None:
                            # Convert BGR image (OpenCV) to RGB format
                            display_image_rgb = cv2.cvtColor(display_image, cv2.COLOR_BGR2RGB)
                            
                            # Convert the RGB image to QImage
                            height, width, channel = display_image_rgb.shape
                            bytes_per_line = 3 * width
                            qimage = QtGui.QImage(display_image_rgb.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
                            
                            # Convert QImage to QPixmap
                            building_pixmap = QtGui.QPixmap.fromImage(qimage)
                            self.predicted_img[aux] = 1
                            # Set the pixmap to QLabel
                            img_frames[aux].setPixmap(
                                building_pixmap.scaled(
                                    img_frames[aux].width(),
                                    img_frames[aux].height(),
                                    QtCore.Qt.IgnoreAspectRatio,  # Adjust scaling mode as needed
                                    QtCore.Qt.SmoothTransformation))  # Ensure high-quality scaling
                    else: 
                        # No building dectection 
                        self.no_image = "No Building detected"
                        # Skipping prection for this image
                        self.predicted_img[aux] = 0
                        font = QtGui.QFont()
                        font.setPointSize(16)
                        font.setBold(True)
                        font.setWeight(75)
                        img_frames[aux].setFont(font)
                        img_frames[aux].setText(self.no_image)
                        img_frames[aux].setAlignment(QtCore.Qt.AlignCenter)  # Center-align text
            
            # There is not GSV image coverage
            else:
                self.no_image = "Street View not available" 
                for aux in range (3):
                    font = QtGui.QFont()
                    font.setPointSize(16)
                    font.setBold(True)
                    font.setWeight(75)
                    img_frames[aux].setFont(font)
                    img_frames[aux].setText(self.no_image)
                    img_frames[aux].setAlignment(QtCore.Qt.AlignCenter)  # Center-align text
        
        # Checking Inspection method (manual option)
        else:
            # Image frames
            img_frames = [self.ui.left_gsv_img, self.ui.central_gsv_img, self.ui.right_gsv_img]
            # Loop for the number of image displayed selected with the option in the coordinates pop-up
            for aux in range (self.n_images_local):
                # Load the image for drawing
                try:
                    img_path = self.ui.folder_path+"/"+str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+".jpg"
                except:
                    QMessageBox.warning(self.ui, "Input Error", "No further inspections are available")
                # Cropped image path (saved in local device)
                cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg")   
                # Display image path (saved in local device)
                displayed_path = (self.ui.folder_path+"/displayed_images/"
                                +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_displayed.jpg")
                # Display building image
                if os.path.exists(displayed_path):
                    # Display an already isolated image
                    building_pixmap = QtGui.QPixmap(displayed_path)
                    # Selection of image frame using "aux" variable
                    img_frames[aux].setPixmap(
                        building_pixmap.scaled(
                            img_frames[aux].width(),
                            img_frames[aux].height(),
                            QtCore.Qt.IgnoreAspectRatio,  # Adjust scaling mode as needed
                            QtCore.Qt.SmoothTransformation))  # Ensure high-quality scaling
                else:
                    # Display a new image
                    if sw == True:
                        # Star progress bar until 99%
                        for i in range (100):
                            time.sleep(0.0001)
                            self.ui.progress_bar_method.setValue(i)
                            self.ui.method_progress.setText("Isolating building ....")
                        sw = False  
                    # Check and/or create cropped folder
                    if not os.path.exists(self.ui.folder_path+"/Cropped_images"):
                        os.makedirs(self.ui.folder_path+"/Cropped_images")
                    # Image results
                    results = model(img_path)
                    image_rgb = cv2.imread(img_path)
                    # Adapting line weight depending of image size, in order to have an appropiate thickness
                    height, width, channels = image_rgb.shape
                    area = height*width
                    ratio = int(area*3/307200)
                    # Lines ratio
                    if area <= 600000:
                        # Small images
                        gap = int(area*14/307200)
                    elif area < 1000000:
                        # Medium images
                        gap = int(area*14/307200 * 3/4)
                    else:
                        # Large images
                        gap = int(area*14/307200 * 3/8)
                        ratio = int(area*3/307200 * 5/8)
                    highest_conf = 0
                    highest_conf_box = None
                    
                    for result in results:
                        boxes = result.boxes.xyxy  # Bounding box coordinates
                        confs = result.boxes.conf  # Confidence scores
                        classes = result.boxes.cls  # Class IDs
                    
                        for box, conf, cls in zip(boxes, confs, classes):
                            cls = int(cls)  # Ensure the class ID is an integer
                            # Getting the building image with higher confidence as selected bounding box
                            if class_map[cls] == "building-xzyh" and conf > highest_conf:
                                highest_conf = conf
                                highest_conf_box = box
                    
                    if highest_conf_box is not None:
                        x1, y1, x2, y2 = map(int, highest_conf_box)
                        
                        # Crop the area within the bounding box
                        cropped_image = image_rgb[y1:y2, x1:x2]
                        # Save image in local device
                        cv2.imwrite(cropped_path, cropped_image)
                    
                        # Draw a dashed red rectangle for the highest confidence box
                        for i in range(x1, x2, gap):
                            cv2.line(image_rgb, (i, y1), (min(i + 5, x2), y1), (0, 0, 255), ratio)  # Top edge
                            cv2.line(image_rgb, (i, y2), (min(i + 5, x2), y2), (0, 0, 255), ratio)  # Bottom edge
                        for i in range(y1, y2, gap):
                            cv2.line(image_rgb, (x1, i), (x1, min(i + 5, y2)), (0, 0, 255), ratio)  # Left edge
                            cv2.line(image_rgb, (x2, i), (x2, min(i + 5, y2)), (0, 0, 255), ratio)  # Right edge
                            
                        # Check and/or create diplayed folder              
                        if not os.path.exists(self.ui.folder_path+"/displayed_images"):
                            os.makedirs(self.ui.folder_path+"/displayed_images")
                        cv2.imwrite(displayed_path, image_rgb)
                        
                        if image_rgb is not None:
                            # Convert BGR image (OpenCV) to RGB format
                            display_image_rgb = cv2.cvtColor(image_rgb, cv2.COLOR_BGR2RGB)
                            # display_image_rgb = image_rgb.copy()
                            # Convert the RGB image to QImage
                            height, width, channel = display_image_rgb.shape
                            bytes_per_line = 3 * width
                            qimage = QtGui.QImage(display_image_rgb.data, width, height, bytes_per_line, QtGui.QImage.Format_RGB888)
                            
                            # Convert QImage to QPixmap
                            building_pixmap = QtGui.QPixmap.fromImage(qimage)
                    
                    # Displayed image in corresponding frames
                    img_frames[aux].setPixmap(
                        building_pixmap.scaled(
                            img_frames[aux].width(),
                            img_frames[aux].height(),
                            QtCore.Qt.IgnoreAspectRatio,  # Adjust scaling mode as needed
                            QtCore.Qt.SmoothTransformation))  # Ensure high-quality scaling
                      
        # Chance progress bar to complete
        self.ui.progress_bar_method.setValue(100)
        self.ui.method_progress.setText("Done!")
        
            
    ############ Left Bounding Box Manual Selection ################
    def bounding_box_frame_left(self):
        """
        Select the left frame image for building detection and retrieve its corresponding path.
    
        This method determines the appropriate source image for the left frame based on the selected 
        inspection mode. If the inspection mode is not manual (`insp_method != 2`), the image is 
        retrieved from Google Street View (GSV). Otherwise, the image is loaded from the local device.
        """
        # Getting the image depending of the inspection mode selected.
        if self.ui.insp_method !=2:
            # From GSV (Polygon and Specific method)
            self.image_bb = self.img_orginial_1
        else:
            # From local device 
            self.image_bb = self.ui.folder_path+"/"+str(self.data_building.iloc[self.click_count * self.n_images_local, 0])+".jpg"
        # Left Frame to display
        self.frame_bb_disp = self.ui.left_gsv_img
        
        # Getting the path for image prediction
        if self.ui.insp_method == 2:
            try:
                # Cropped image path
                self.cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                     +str(self.data_building.iloc[self.click_count * self.n_images_local, 0])+"_cropped.jpg") 
            except:
                QMessageBox.warning(self.ui, "File Error", "This option is only available if there is a previous building detection.")
        else:
            self.cropped_path = None
    
    
    ############ Left Bounding Box Manual Selection ################       
    def bounding_box_frame_central(self):
        """
        Select the central frame image for building detection and retrieve its corresponding path.
    
        This method determines the appropriate source image for the left frame based on the selected 
        inspection mode. If the inspection mode is not manual (`insp_method != 2`), the image is 
        retrieved from Google Street View (GSV). Otherwise, the image is loaded from the local device.
        """
        # Getting the image depending of the inspection mode selected.
        if self.ui.insp_method !=2: 
            # From GSV (Polygon and Specific method)
            self.image_bb = self.img_orginial_2
        else:
            # From local device 
            self.image_bb = self.ui.folder_path+"/"+str(self.data_building.iloc[self.click_count * self.n_images_local + 1, 0])+".jpg"
        # Central Frame to display 
        self.frame_bb_disp = self.ui.central_gsv_img
        
        # Getting the path for image prediction
        if self.ui.insp_method == 2:
            try:
                # Cropped image path
                self.cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                      +str(self.data_building.iloc[self.click_count * self.n_images_local + 1, 0])+"_cropped.jpg")
            except:
                QMessageBox.warning(self.ui, "File Error", "This option is only available if there is a previous building detection.")
        else:
            self.cropped_path = None
    
            
    ############ Right Bounding Box Manual Selection ################
    def bounding_box_frame_right(self):
        """
        Select the right frame image for building detection and retrieve its corresponding path.
    
        This method determines the appropriate source image for the left frame based on the selected 
        inspection mode. If the inspection mode is not manual (`insp_method != 2`), the image is 
        retrieved from Google Street View (GSV). Otherwise, the image is loaded from the local device.
        """
        # Getting the image depending of the inspection mode selected.
        if self.ui.insp_method !=2:
            # From GSV (Polygon and Specific method)
            self.image_bb = self.img_orginial_3
        else:
            # From local device 
            self.image_bb = self.ui.folder_path+"/"+str(self.data_building.iloc[self.click_count * self.n_images_local + 2, 0])+".jpg"
        
        self.frame_bb_disp = self.ui.right_gsv_img
        # Getting the path for image prediction
        if self.ui.insp_method == 2:
            try:
                # Cropped image path
                self.cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                     +str(self.data_building.iloc[self.click_count * self.n_images_local + 2, 0])+"_cropped.jpg")   
            except:
                QMessageBox.warning(self.ui, "File Error", "This option is only available if there is a previous building detection.")
            
            
    ############ Folder Selection ################
    def bounding_box(self):
        """
        Open a bounding box selection pop-up for manual annotation.
    
        This method allows the user to manually define a bounding box around a building 
        in an image by selecting four points. The bounding box is then displayed in the UI 
        frame. Before execution, the method verifies that the project folder, country, and 
        city name are correctly set.
    
        Notes:
            - If the AI-powered option is enabled, users must manually label the building 
              or verify that existing labels are correct.
            - Ensures a valid PyQt5 `QApplication` instance exists before opening the pop-up.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            QMessageBox.warning(self.ui, "File Error", "This option is only available once the building image is displayed.")
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            QMessageBox.warning(self.ui, "This option is only available once the building image is displayed.")
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            QMessageBox.warning(self.ui, "This option is only available once the building image is displayed.")
        else:
            
            """Open the bounding box selection pop-up window."""
            app = QApplication.instance()  # Ensure PyQt instance exists
            if app is None:
                app = QApplication([])
                
            # Called function where the user creates a manual bounding box by clicking four points, which is then displayed in the UI frame.
            dialog = BoundingBoxWindow(self.image_bb, self.frame_bb_disp, self.ui.insp_method, self.cropped_path)
            dialog.exec_()  # Open the pop-up
            # For polygon and specfic method 
            if self.ui.insp_method != 2:
                # Get cropped image in memory
                self.cropped_image = dialog.prediction_img
            
            # Message with special format
            message = """
            If you are making predictions using the AI-powered option, when a manual bounding box is created, 
            <b><u>NO NEW PREDICTION EXECUTION OCCURS</u></b>. For this, you should manually label the building 
            or verify that the current labels correspond to the true labels.
            """
            
            # Create a QMessageBox instance
            msg_box = QMessageBox(self.ui)
            msg_box.setTextFormat(QtCore.Qt.RichText)
            msg_box.setText(message)
            msg_box.setWindowTitle("AI-powered inspection form")
            
            # Show the message box
            msg_box.exec_()
            

        
    ############ Obtain value of the form of each building image ################       
    def inspection_database (self):
        """
        Populate the inspection database with data extracted from building images and user inputs.
    
        This method collects information for three building images (left, central, right) and appends 
        the data to the inspection database. Data includes geographic coordinates, building attributes, 
        and user-provided metadata from the UI fields. Each building's data is treated as a separate 
        entry in the database.
    
        Args:
            None. The method operates on instance attributes such as `click_count`, `data_building`, 
            and various UI elements for user inputs and data display.
    
        Returns:
            None. The collected data is appended to `self.ui.database`.
    
        Effects:
            - Updates `self.ui.database` with building attributes and metadata for the current 
              set of images.
            - Gathers inputs such as material type, lateral load-resisting system (LLRS), code level, 
              number of stories, occupancy, block position, and image quality.
    
        Notes:
            - The database is populated only if `click_count` is greater than zero.
            - Assumes the `data_building` DataFrame contains valid latitude and longitude values.
            - Each entry in the database corresponds to a specific building image.
            - Requires properly configured UI components to retrieve and store data.
        """
        
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:    
            
            if self.ui.insp_method != 2:
                base_url = "https://www.google.com/maps/@?api=1&map_action=pano&viewpoint="
                coord = str(self.ui.lat_value.text()) + "," + str(self.ui.lon_value.text())
                heading = get_road_orientation((float(self.ui.lat_value.text()), float(self.ui.lon_value.text())))
                
            # Left building image
            self.data_ai.iloc[self.click_count * 3 , 0] = self.ui.img_id_value_1.text()                  # ID
            self.data_ai.iloc[self.click_count * 3 , 1] = self.data_building.iloc[self.click_count,1]    # Latitude
            self.data_ai.iloc[self.click_count * 3 , 2] = self.data_building.iloc[self.click_count,2]    # Longitude
            self.data_ai.iloc[self.click_count * 3 , 3] = self.ui.country_value.text()                   # Country
            self.data_ai.iloc[self.click_count * 3 , 4] = self.ui.city_value.text()                      # City
            self.data_ai.iloc[self.click_count * 3 , 5] = self.ui.material_cb_1.currentData()            # LLRS Material
            self.data_ai.iloc[self.click_count * 3 , 6] = self.ui.llrs_cb_1.currentData()                # LLRS 
            self.data_ai.iloc[self.click_count * 3 , 7] = self.ui.age_cb_1.currentData()                 # Code Level 
            self.data_ai.iloc[self.click_count * 3 , 8] = self.ui.n_stories_value_1.currentData()        # Number of Stories 
            self.data_ai.iloc[self.click_count * 3 , 9] = self.ui.occup_cb_1.currentData()               # Occupancy
            self.data_ai.iloc[self.click_count * 3 , 10] = self.ui.bck_pos_cb_1.currentData()            # Block Position
            self.data_ai.iloc[self.click_count * 3 , 11] = self.ui.img_q_cb_1.currentData()              # Image Quality
            
            try:
                self.data_ai.iloc[self.click_count * 3 , 12] = (self.ui.material_cb_1.currentData()+"/"+self.ui.llrs_cb_1.currentData()
                                                                +"/HEX:"+self.ui.n_stories_value_1.currentText()+"/"+
                                                                "CODE:"+self.ui.age_cb_1.currentData())            # Taxonomy
            except:
                pass
            
            if self.ui.insp_method != 2:
                if self.img_url[0]  != "":
                    self.data_ai.iloc[self.click_count * 3 , 13] = self.img_url[0]                           # Image URL
                else:
                    if isinstance(heading, int):
                        self.data_ai.iloc[self.click_count * 3 , 13] = base_url + coord +"&heading="+str((heading+ 150) % 360)+"&pitch=5&fov=120"
            else:
                self.data_ai.iloc[self.click_count * 3 , 13] = self.data_building.iloc[self.click_count * self.n_images_local , 0] 
                
            # Central building image
            # AI values
            self.data_ai.iloc[self.click_count * 3 + 1, 0] = self.ui.img_id_value_2.text()                  # ID
            self.data_ai.iloc[self.click_count * 3 + 1, 1] = self.data_building.iloc[self.click_count,1]    # Latitude
            self.data_ai.iloc[self.click_count * 3 + 1, 2] = self.data_building.iloc[self.click_count,2]    # Longitude
            self.data_ai.iloc[self.click_count * 3 + 1, 3] = self.ui.country_value.text()                   # Country
            self.data_ai.iloc[self.click_count * 3 + 1, 4] = self.ui.city_value.text()                      # City
            self.data_ai.iloc[self.click_count * 3 + 1, 5] = self.ui.material_cb_2.currentData()            # LLRS Material
            self.data_ai.iloc[self.click_count * 3 + 1, 6] = self.ui.llrs_cb_2.currentData()                # LLRS 
            self.data_ai.iloc[self.click_count * 3 + 1, 7] = self.ui.age_cb_2.currentData()                 # Code Level 
            self.data_ai.iloc[self.click_count * 3 + 1, 8] = self.ui.n_stories_value_2.currentData()        # Number of Stories 
            self.data_ai.iloc[self.click_count * 3 + 1, 9] = self.ui.occup_cb_2.currentData()               # Occupancy
            self.data_ai.iloc[self.click_count * 3 + 1, 10] = self.ui.bck_pos_cb_2.currentData()            # Block Position
            self.data_ai.iloc[self.click_count * 3 + 1, 11] = self.ui.img_q_cb_2.currentData()              # Image Quality
            
            try:
                self.data_ai.iloc[self.click_count * 3 + 1, 12] = (self.ui.material_cb_2.currentData()+"/"+self.ui.llrs_cb_2.currentData()
                                                                +"/HEX:"+self.ui.n_stories_value_2.currentText()+"/"+
                                                                "CODE:"+self.ui.age_cb_2.currentData())            # Taxonomy
            except:
                pass
            
            if self.ui.insp_method != 2:
                if self.img_url[1]  != "":
                    self.data_ai.iloc[self.click_count * 3 + 1, 13] = self.img_url[1]                           # Image URL
                else:
                    if isinstance(heading, int):
                        self.data_ai.iloc[self.click_count * 3 + 1, 13] = base_url + coord +"&heading="+str((heading+ 180) % 360)+"&pitch=5&fov=120"
            else:
                if self.n_images_local >= 2:
                    self.data_ai.iloc[self.click_count * 3 + 1, 13] = self.data_building.iloc[self.click_count * self.n_images_local + 1, 0] 
            
            
            # # Exposure model values
            # self.data_expo.iloc[self.click_count, 0] = self.ui.img_id_value_2.text()                  # ID
            # self.data_expo.iloc[self.click_count, 1] = self.data_building.iloc[self.click_count,1]    # Latitude
            # self.data_expo.iloc[self.click_count, 2] = self.data_building.iloc[self.click_count,2]    # Longitude
            # self.data_expo.iloc[self.click_count, 3] = self.ui.country_value.text()                   # Country
            # self.data_expo.iloc[self.click_count, 4] = self.ui.city_value.text()                      # City
            # self.data_expo.iloc[self.click_count, 5] = self.ui.material_cb_2.currentData()            # LLRS Material
            # self.data_expo.iloc[self.click_count, 6] = self.ui.llrs_cb_2.currentData()                # LLRS 
            # self.data_expo.iloc[self.click_count, 7] = self.ui.age_cb_2.currentData()                 # Code Level 
            # self.data_expo.iloc[self.click_count, 8] = self.ui.n_stories_value_2.value()              # Number of Stories 
            # self.data_expo.iloc[self.click_count, 9] = self.ui.occup_cb_2.currentData()               # Occupancy
            # self.data_expo.iloc[self.click_count, 10] = self.ui.bck_pos_cb_2.currentData()            # Block Position
            # self.data_expo.iloc[self.click_count, 11] = self.ui.img_q_cb_2.currentData()              # Image Quality
               
            
            # Right building image
            self.data_ai.iloc[self.click_count * 3 + 2, 0] = self.ui.img_id_value_3.text()                  # ID
            self.data_ai.iloc[self.click_count * 3 + 2, 1] = self.data_building.iloc[self.click_count,1]    # Latitude
            self.data_ai.iloc[self.click_count * 3 + 2, 2] = self.data_building.iloc[self.click_count,2]    # Longitude
            self.data_ai.iloc[self.click_count * 3 + 2, 3] = self.ui.country_value.text()                   # Country
            self.data_ai.iloc[self.click_count * 3 + 2, 4] = self.ui.city_value.text()                      # City
            self.data_ai.iloc[self.click_count * 3 + 2, 5] = self.ui.material_cb_3.currentData()            # LLRS Material
            self.data_ai.iloc[self.click_count * 3 + 2, 6] = self.ui.llrs_cb_3.currentData()                # LLRS 
            self.data_ai.iloc[self.click_count * 3 + 2, 7] = self.ui.age_cb_3.currentData()                 # Code Level 
            self.data_ai.iloc[self.click_count * 3 + 2, 8] = self.ui.n_stories_value_3.currentData()        # Number of Stories 
            self.data_ai.iloc[self.click_count * 3 + 2, 9] = self.ui.occup_cb_3.currentData()               # Occupancy
            self.data_ai.iloc[self.click_count * 3 + 2, 10] = self.ui.bck_pos_cb_3.currentData()            # Block Position
            self.data_ai.iloc[self.click_count * 3 + 2, 11] = self.ui.img_q_cb_3.currentData()              # Image Quality
            
            try:
                self.data_ai.iloc[self.click_count * 3 + 2, 12] = (self.ui.material_cb_3.currentData()+"/"+self.ui.llrs_cb_3.currentData()
                                                                +"/HEX:"+self.ui.n_stories_value_3.currentText()+"/"+
                                                                "CODE:"+self.ui.age_cb_3.currentData())            # Taxonomy
            except:
                pass
            
            if self.ui.insp_method != 2:
                if self.img_url[2]  != "":
                    self.data_ai.iloc[self.click_count * 3 + 2, 13] = self.img_url[2]                           # Image URL
                else:
                    if isinstance(heading, int):
                        self.data_ai.iloc[self.click_count * 3 + 2, 13] = base_url + coord +"&heading="+str((heading+ 210) % 360)+"&pitch=5&fov=120"
            else:
                if self.n_images_local == 3:
                    self.data_ai.iloc[self.click_count * 3 + 2, 13] = self.data_building.iloc[self.click_count * self.n_images_local + 2, 0] 
            
            
    ############ Saves the data from the inspections that were conducted ################       
    def save_database (self):
        """
        Save the inspection data to a CSV file.
    
        This method consolidates new inspection data with any previously saved data and exports 
        the combined dataset to a CSV file. If no prior data exists, it creates a new CSV file 
        containing only the current inspections. The CSV file is named using the city and country 
        information and stored in the specified output folder.
    
        Args:
            None. The method operates on the `self.ui.database` attribute and the UI-provided output folder path.
    
        Returns:
            None. The inspection data is saved or updated in the CSV file.
    
        Effects:
            - Reads previous inspection data from an existing CSV file (if available).
            - Appends the new inspection data to the existing dataset.
            - Exports the combined dataset to a CSV file in the specified output folder.
    
        Notes:
            - The CSV file is named with the pattern `<city>_<country>_inspection.csv`.
            - Handles exceptions gracefully when no previous CSV file exists.
            - Calls `self.inspection_database()` to gather new inspection data before saving.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Load path 
            output_folder = self.ui.output_folder_value.text()
            img_prefix = f"{output_folder}/{self.city_method}_{self.country_method}"
    
            # Create CSV with new inspections
            self.inspection_database()
            
            # Star progress bar
            self.ui.method_progress.setText("Saving inspections ...")
            for j in range (101):
                time.sleep(0.0001)
                self.ui.progress_bar_method.setValue(j)
            # Save inspections
            ############################## Polygon #######################################
            if self.ui.insp_method == 0:
                try:
                    # Save the AI inspection data to a CSV file
                    self.data_ai.to_csv(img_prefix + "_AI_inspections.csv", index=False)
                    # Save the exposure inspection data to a CSV file
                    self.data_expo.to_csv(img_prefix + "_EXPO_inspections.csv", index=False)
                    # Update the progress message in the GUI
                    self.ui.method_progress.setText("Inspections exported successfully!")
                except:
                    # Show a warning message box if there's a permission error
                    QMessageBox.warning(self.ui, "File Error", "The file is open or the folder is inaccessible."
                                        +"Please close the file or check folder permissions.")
            ############################## Specific #######################################
            elif self.ui.insp_method == 1:
                try:
                    # Save the AI inspection data to a CSV file
                    self.data_ai.to_csv(self.ui.output_folder_value.text()+"/"+self.ui.file_name+"_AI_inspections.csv", index=False)
                    
                    # Save the exposure inspection data to a CSV file
                    self.data_expo.to_csv(self.ui.output_folder_value.text()+"/"+self.ui.file_name+"_EXPO_inspections.csv", index=False)
                    # Update the progress message in the GUI
                    self.ui.method_progress.setText("Inspections exported successfully!")
                except:
                    # Show a warning message box if there's a permission error
                    QMessageBox.warning(self.ui, "File Error", "The file is open or the folder is inaccessible."
                                        +"Please close the file or check folder permissions.")
            ############################## Local #######################################
            elif self.ui.insp_method == 2:
                try:
                    # Save the AI inspection data to a CSV file
                    self.data_ai.to_csv(self.ui.output_folder_value.text()+"/"+self.ui.file_name_local+"_AI_inspections.csv", index=False)
                    
                    # Save the exposure inspection data to a CSV file
                    self.data_expo.to_csv(self.ui.output_folder_value.text()+"/"+self.ui.file_name_local+"_EXPO_inspections.csv", index=False)
                    # Update the progress message in the GUI
                    self.ui.method_progress.setText("Inspections exported successfully!")
                except:
                    # Show a warning message box if there's a permission error
                    QMessageBox.warning(self.ui, "File Error", "The file is open or the folder is inaccessible."
                                        +"Please close the file or check folder permissions.")
            
            
            self.data_old = "OK" # TO BE SAVED THERE IS EXISTING DATA
            self.sw_insp = True
            self.save_id = True
            self.start = True
            
            
    def setComboBoxByData(self, comboBox, data):
        """
        Set the index of a QComboBox based on its associated data value.
    
        This method iterates through the items in a `QComboBox` and selects the index 
        corresponding to the provided `data` value. If a match is found, the combo box 
        is updated to that index. If no match is found, the default return value is an 
        empty string.
    
        Args:
            comboBox (QComboBox): The combo box to update.
            data (Any): The data value to search for within the combo box items.
    
        Returns:
            str: Returns an empty string if no match is found; otherwise, returns the 
                 result of `setCurrentIndex(i)`, though `setCurrentIndex` does not 
                 explicitly return a value.
    
        Effects:
            - Updates the `comboBox` selection if a matching data value is found.
    
        Notes:
            - If no match is found, the combo box remains unchanged.
            - The method assumes `comboBox.itemData(i)` correctly retrieves stored data values.
        """
        # Iterate through the comboBox items to find the one with matching data
        match_data = [""]
        for i in range(comboBox.count()):
            if comboBox.itemData(i) == data:
                match_data = comboBox.setCurrentIndex(i)
                break
        return match_data
        
        
    ############ Restart default value of each building feature ################  
    def clean_database (self):
        """
        Reset the UI fields for building features to their default values.
    
        This method clears and resets all inputs related to the building features for the left, 
        central, and right building images. It sets dropdown menus to default selections, 
        numeric fields to zero, and other UI components to their initial states.
    
        Args:
            None. The method operates on UI elements for user inputs.
    
        Returns:
            None. The UI fields for building features are reset to their default values.
    
        Effects:
            - Resets dropdowns for material type, lateral load-resisting system (LLRS), code level, 
              occupancy type, block position, and image quality to default values.
            - Resets numeric fields for the number of stories to zero.
    
        Notes:
            - This method ensures that the UI is cleared and ready for new input after processing 
              or a reset action.
            - Requires properly configured UI elements to work as intended.
        """
        # Restart default value of left building image
        
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Material
            if self.data_ai.iloc[self.click_count * 3 , 5] is None:
                self.ui.material_cb_1.setCurrentText("Select Material")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 5]) == True:
                self.ui.material_cb_1.setCurrentText("Select Material")
            else:
                self.setComboBoxByData(self.ui.material_cb_1 , self.data_ai.iloc[self.click_count * 3 , 5])
    
            # LLRS
            if self.data_ai.iloc[self.click_count * 3 , 6] is None :
                self.ui.llrs_cb_1.setCurrentText("Select LLRS")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 6]) == True:
                self.ui.llrs_cb_1.setCurrentText("Select LLRS")
            else:
                self.setComboBoxByData(self.ui.llrs_cb_1 , self.data_ai.iloc[self.click_count * 3 , 6])
                
            # Code level
            if self.data_ai.iloc[self.click_count * 3 , 7] is None :
                self.ui.age_cb_1.setCurrentText("Select Code Level")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 7]) == True:
                self.ui.age_cb_1.setCurrentText("Select Code Level")
            else:
                self.setComboBoxByData(self.ui.age_cb_1 , self.data_ai.iloc[self.click_count * 3 , 7])
            
            # Number of stories
            if self.data_ai.iloc[self.click_count * 3 , 8] is None :
                self.ui.n_stories_value_1.setCurrentText("Select Number of Stories")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 8]) == True:
                self.ui.n_stories_value_1.setCurrentText("Select Number of Stories")
            else:
                self.setComboBoxByData(self.ui.n_stories_value_1, self.data_ai.iloc[self.click_count * 3 , 8])
                
            # Occupancy
            if self.data_ai.iloc[self.click_count * 3 , 9] is None :
                self.ui.occup_cb_1.setCurrentText("Select Occupancy Type")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 9]) == True:
                self.ui.occup_cb_1.setCurrentText("Select Occupancy Type")
            else:
                self.setComboBoxByData(self.ui.occup_cb_1 , self.data_ai.iloc[self.click_count * 3 , 9])
            
            # Block Position
            if self.data_ai.iloc[self.click_count * 3 , 10] is None :
                self.ui.bck_pos_cb_1.setCurrentText("Select Block Position")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 10]) == True:
                self.ui.bck_pos_cb_1.setCurrentText("Select Block Position")
            else:
                self.setComboBoxByData(self.ui.bck_pos_cb_1 , self.data_ai.iloc[self.click_count * 3 , 10])
    
            # Image quality
            if self.data_ai.iloc[self.click_count * 3 , 11] is None :
                self.ui.img_q_cb_1.setCurrentText("Select Image Quality")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 , 11]) == True:
                self.ui.img_q_cb_1.setCurrentText("Select Image Quality")
            else:
                self.setComboBoxByData(self.ui.img_q_cb_1 , self.data_ai.iloc[self.click_count * 3 , 11])
                
                
            # Restart default value of central building image
            # Material
            if self.data_ai.iloc[self.click_count * 3 + 1 , 5] is None:
                self.ui.material_cb_2.setCurrentText("Select Material")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 5]) == True:
                self.ui.material_cb_2.setCurrentText("Select Material")
            else:
                self.setComboBoxByData(self.ui.material_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 5])
    
            # LLRS
            if self.data_ai.iloc[self.click_count * 3 + 1 , 6] is None :
                self.ui.llrs_cb_2.setCurrentText("Select LLRS")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 6]) == True:
                self.ui.llrs_cb_2.setCurrentText("Select LLRS")
            else:
                self.setComboBoxByData(self.ui.llrs_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 6])
                
            # Code level
            if self.data_ai.iloc[self.click_count * 3 + 1 , 7] is None :
                self.ui.age_cb_2.setCurrentText("Select Code Level")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 7]) == True:
                self.ui.age_cb_2.setCurrentText("Select Code Level")
            else:
                self.setComboBoxByData(self.ui.age_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 7])
            
            # Number of stories
            if self.data_ai.iloc[self.click_count * 3 + 1 , 8] is None :
                self.ui.n_stories_value_2.setCurrentText("Select Number of Stories")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 8]) == True:
                self.ui.n_stories_value_2.setCurrentText("Select Number of Stories")
            else:
                self.setComboBoxByData(self.ui.n_stories_value_2, self.data_ai.iloc[self.click_count * 3 + 1, 8])
                
            # Occupancy
            if self.data_ai.iloc[self.click_count * 3 + 1 , 9] is None :
                self.ui.occup_cb_2.setCurrentText("Select Occupancy Type")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 9]) == True:
                self.ui.occup_cb_2.setCurrentText("Select Occupancy Type")
            else:
                self.setComboBoxByData(self.ui.occup_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 9])
            
            # Block Position
            if self.data_ai.iloc[self.click_count * 3 + 1 , 10] is None :
                self.ui.bck_pos_cb_2.setCurrentText("Select Block Position")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 10]) == True:
                self.ui.bck_pos_cb_2.setCurrentText("Select Block Position")
            else:
                self.setComboBoxByData(self.ui.bck_pos_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 10])
    
            # Image quality
            if self.data_ai.iloc[self.click_count * 3 + 1 , 11] is None :
                self.ui.img_q_cb_2.setCurrentText("Select Image Quality")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 1 , 11]) == True:
                self.ui.img_q_cb_2.setCurrentText("Select Image Quality")
            else:
                self.setComboBoxByData(self.ui.img_q_cb_2 , self.data_ai.iloc[self.click_count * 3 + 1 , 11])
    
            # Restart default value of right building image
            # Material
            if self.data_ai.iloc[self.click_count * 3 + 2 , 5] is None:
                self.ui.material_cb_3.setCurrentText("Select Material")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 5]) == True:
                self.ui.material_cb_3.setCurrentText("Select Material")
            else:
                self.setComboBoxByData(self.ui.material_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 5])
    
            # LLRS
            if self.data_ai.iloc[self.click_count * 3 + 2 , 6] is None :
                self.ui.llrs_cb_3.setCurrentText("Select LLRS")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 6]) == True:
                self.ui.llrs_cb_3.setCurrentText("Select LLRS")
            else:
                self.setComboBoxByData(self.ui.llrs_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 6])
                
            # Code level
            if self.data_ai.iloc[self.click_count * 3 + 2 , 7] is None :
                self.ui.age_cb_3.setCurrentText("Select Code Level")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 7]) == True:
                self.ui.age_cb_3.setCurrentText("Select Code Level")
            else:
                self.setComboBoxByData(self.ui.age_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 7])
            
            # Number of stories
            if self.data_ai.iloc[self.click_count * 3 + 2 , 8] is None :
                self.ui.n_stories_value_3.setCurrentText("Select Number of Stories")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 8]) == True:
                self.ui.n_stories_value_3.setCurrentText("Select Number of Stories")
            else:
                self.setComboBoxByData(self.ui.n_stories_value_3, self.data_ai.iloc[self.click_count * 3 + 2, 8])
                
            # Occupancy
            if self.data_ai.iloc[self.click_count * 3 + 2 , 9] is None :
                self.ui.occup_cb_3.setCurrentText("Select Occupancy Type")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 9]) == True:
                self.ui.occup_cb_3.setCurrentText("Select Occupancy Type")
            else:
                self.setComboBoxByData(self.ui.occup_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 9])
            
            # Block Position
            if self.data_ai.iloc[self.click_count * 3 + 2 , 10] is None :
                self.ui.bck_pos_cb_3.setCurrentText("Select Block Position")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 10]) == True:
                self.ui.bck_pos_cb_3.setCurrentText("Select Block Position")
            else:
                self.setComboBoxByData(self.ui.bck_pos_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 10])
    
            # Image quality
            if self.data_ai.iloc[self.click_count * 3 + 2 , 11] is None :
                self.ui.img_q_cb_3.setCurrentText("Select Image Quality")
            elif pd.isna(self.data_ai.iloc[self.click_count * 3 + 2 , 11]) == True:
                self.ui.img_q_cb_3.setCurrentText("Select Image Quality")
            else:
                self.setComboBoxByData(self.ui.img_q_cb_3 , self.data_ai.iloc[self.click_count * 3 + 2 , 11])
            
     
    ############ Deep learning model for predict the LLRS Material ################
    def material_prediction (self, image_file):
        """
        Predict the Material of the Lateral Load Resisting System (LLRS) of a building using a deep learning model.
    
        This method applies a deep learning model to predict the LLRS Material for three building images 
        (e.g., from Google Street View). If the AI-powered checkbox is activated in the UI, the 
        method processes each image, retrieves predictions, and updates the corresponding UI 
        comboboxes with the predicted LLRS Material values.
    
        Args:
            image_file (str): Path to the image file being processed (unused within the function body).
    
        Returns:
            None. The predicted LLRS values are set in the UI comboboxes.
    
        Effects:
            - Loads and applies a deep learning model to predict LLRS for the images.
            - Updates the comboboxes (`material_cb_1`, `material_cb_2`, `material_cb_3`) in the UI with predictions.
            - Updates the progress bar and status message in the UI.
    
        Notes:
            - The progress bar provides visual feedback during model loading and prediction.
            - Handles exceptions silently if predictions or UI updates fail.
            - Requires the AI-powered checkbox (`ai_check`) to be selected for predictions to proceed.
            - Assumes a predefined function `predict_material_img` for making predictions.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            material_id = [self.ui.material_cb_1,self.ui.material_cb_2,self.ui.material_cb_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                    for i in range (3):
                        # Image path
                        if self.predicted_img[i] == 1:
                            image_file = self.cropped_image
                            # LLRS building image prediction
                            material_index = predict_material_img(image_file, self.ui.insp_method)
                      
                            # Set DL model prediction
                            # LLRS building image sets prediction
                            material_id[i].setCurrentIndex(material_index+1)
                     
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        
                        # LLRS building image prediction
                        material_index = predict_material_img(cropped_path, self.ui.insp_method)
                        # LLRS building image sets prediction
                        material_id[aux].setCurrentIndex(material_index+1)
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                        
                        
    ############ Deep learning model for predict the LLRS ################
    def llrs_prediction (self, image_file):
        """
        Predict the Lateral Load Resisting System (LLRS) of a building using a deep learning model.
    
        This method applies a deep learning model to predict the LLRS for three building images 
        (e.g., from Google Street View). If the AI-powered checkbox is activated in the UI, the 
        method processes each image, retrieves predictions, and updates the corresponding UI 
        comboboxes with the predicted LLRS values.
    
        Args:
            image_file (str): Path to the image file being processed (unused within the function body).
    
        Returns:
            None. The predicted LLRS values are set in the UI comboboxes.
    
        Effects:
            - Loads and applies a deep learning model to predict LLRS for the images.
            - Updates the comboboxes (`llrs_cb_1`, `llrs_cb_2`, `llrs_cb_3`) in the UI with predictions.
            - Updates the progress bar and status message in the UI.
    
        Notes:
            - The progress bar provides visual feedback during model loading and prediction.
            - Handles exceptions silently if predictions or UI updates fail.
            - Requires the AI-powered checkbox (`ai_check`) to be selected for predictions to proceed.
            - Assumes a predefined function `predict_llrs_img` for making predictions.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            llrs_id = [self.ui.llrs_cb_1,self.ui.llrs_cb_2,self.ui.llrs_cb_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    for i in range (3):
                        if self.predicted_img[i] == 1:
                            # Image path
                            image_file = self.cropped_image        
                            # LLRS building image prediction
                            llrs_index = predict_llrs_img(image_file, self.ui.insp_method)
                            # LLRS building image sets prediction
                            llrs_id[i].setCurrentIndex(llrs_index+1) 
                            
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        
                        # LLRS building image prediction
                        llrs_index = predict_llrs_img(cropped_path, self.ui.insp_method)
                        # LLRS building image sets prediction
                        llrs_id[aux].setCurrentIndex(llrs_index+1)
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                        
                        
    ############ Deep learning model for predict the Code level ################
    def code_level_prediction (self, image_file):
        """
        Predict and assign a code level to a building based on its image.
    
        This method utilizes an AI model to predict the structural code level of a building 
        from an image. It first ensures that the necessary project details (folder, country, 
        and city) are set before execution. If AI-powered prediction is enabled, it processes 
        the images and updates the corresponding UI elements with the predicted code level.
    
        Args:
            image_file (str): Path to the building image file to be analyzed.
    
        Effects:
            - Uses an AI model to predict the structural code level of the building.
            - Updates the UI combo boxes (`age_cb_1`, `age_cb_2`, `age_cb_3`) with the predicted values.
            - Displays progress updates via the UI progress bar.
            - Handles both Google Street View (GSV) and local image-based inspections.
    
        Notes:
            - AI-based prediction is performed only if the AI checkbox (`ai_check`) is enabled.
            - In polygon-based and specific inspection modes (`insp_method != 2`), 
              cropped images are used for prediction.
            - For manual inspection mode (`insp_method == 2`), predictions are performed 
              on local cropped images.
            - The `predict_code_img` function is called to generate predictions.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            code_level_id = [self.ui.age_cb_1,self.ui.age_cb_2,self.ui.age_cb_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    for i in range (3):
                        if self.predicted_img[i] == 1:
                            # Image path
                            image_file = self.cropped_image
    
                            # LLRS building image prediction
                            code_level_index = predict_code_img(image_file, self.ui.insp_method)
    
                            # LLRS building image sets prediction
                            code_level_id[i].setCurrentIndex(code_level_index+1)                      
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        # LLRS building image prediction
                        code_level_index = predict_code_img(cropped_path, self.ui.insp_method)
                        # LLRS building image sets prediction
                        code_level_id[aux].setCurrentIndex(code_level_index+1)
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                    
     
    ############ Deep learning model for predict the Number of Stories ################
    def n_stories_prediction (self, image_file):
        """
        Predict the Lateral Load Resisting System (LLRS) of a building using a deep learning model.
    
        This method applies a deep learning model to predict the LLRS for three building images 
        (e.g., from Google Street View). If the AI-powered checkbox is activated in the UI, the 
        method processes each image, retrieves predictions, and updates the corresponding UI 
        comboboxes with the predicted LLRS values.
    
        Args:
            image_file (str): Path to the image file being processed (unused within the function body).
    
        Returns:
            None. The predicted LLRS values are set in the UI comboboxes.
    
        Effects:
            - Loads and applies a deep learning model to predict LLRS for the images.
            - Updates the comboboxes (`llrs_cb_1`, `llrs_cb_2`, `llrs_cb_3`) in the UI with predictions.
            - Updates the progress bar and status message in the UI.
    
        Notes:
            - The progress bar provides visual feedback during model loading and prediction.
            - Handles exceptions silently if predictions or UI updates fail.
            - Requires the AI-powered checkbox (`ai_check`) to be selected for predictions to proceed.
            - Assumes a predefined function `predict_llrs_img` for making predictions.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            n_stories_id = [self.ui.n_stories_value_1,self.ui.n_stories_value_2,self.ui.n_stories_value_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    for i in range (3):
                        if self.predicted_img[i] == 1:
                            # Image path
                            image_file = self.cropped_image
        
                            # LLRS building image prediction
                            n_stories_index = predict_n_stories_img(image_file, self.ui.insp_method)
        
                            # LLRS building image sets prediction
                            class_names = ['10-12', '13+', '1', '2', '3', '4', '5', '6-7', '8-9']
                            n_stories_id[i].setCurrentText(class_names[n_stories_index])    
                            
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        
                        # LLRS building image prediction
                        n_stories_index = predict_n_stories_img(cropped_path, self.ui.insp_method)
                        # LLRS building image sets prediction
                        class_names = ['10-12', '13+', '1', '2', '3', '4', '5', '6-7', '8-9']
                        n_stories_id[aux].setCurrentText(class_names[n_stories_index])
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                        
                        
    ############ Deep learning model for predict the Occupancy type ################
    def occupancy_prediction (self, image_file):
        """
        Predict and assign an occupancy classification to a building based on its image.
    
        This method utilizes an AI model to predict the occupancy class of a building 
        from an image. It ensures that necessary project details (folder, country, 
        and city) are set before execution. If AI-powered prediction is enabled, it 
        processes the images and updates the corresponding UI elements with the 
        predicted occupancy class.
    
        Args:
            image_file (str): Path to the building image file to be analyzed.
    
        Effects:
            - Uses an AI model to predict the occupancy classification of the building.
            - Updates the UI combo boxes (`occup_cb_1`, `occup_cb_2`, `occup_cb_3`) 
              with the predicted occupancy class.
            - Displays progress updates via the UI progress bar.
            - Handles both Google Street View (GSV) and local image-based inspections.
    
        Notes:
            - AI-based prediction is performed only if the AI checkbox (`ai_check`) is enabled.
            - In polygon-based and specific inspection modes (`insp_method != 2`), 
              cropped images are used for prediction.
            - For manual inspection mode (`insp_method == 2`), predictions are performed 
              on local cropped images.
        """
        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            occupancy_id = [self.ui.occup_cb_1,self.ui.occup_cb_2,self.ui.occup_cb_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    for i in range (3):
                        if self.predicted_img[i] == 1:
                            # Image path
                            image_file = self.cropped_image
    
                            # LLRS building image prediction
                            occupancy_index = predict_occupancy_img(image_file, self.ui.insp_method)
    
                            # LLRS building image sets prediction
                            occupancy_class = ['Residential', 'Educational', 'Government', 'Industrial', 'Mixed', 'Other', 'Residential']
                            occupancy_id[i].setCurrentText(occupancy_class[occupancy_index])                      
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        
                        # LLRS building image prediction
                        occupancy_index = predict_occupancy_img(cropped_path, self.ui.insp_method)
                        # LLRS building image sets prediction
                        occupancy_class = ['Residential', 'Educational', 'Government', 'Industrial', 'Mixed', 'Other', 'Residential']
                        occupancy_id[aux].setCurrentText(occupancy_class[occupancy_index])     
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                        
                        
    ############ Deep learning model for predict the block_position ################
    def block_position_prediction (self, image_file):
        """
        Predict and assign a block position classification to a building based on its image.
    
        This method utilizes an AI model to predict the block position of a building 
        from an image. It ensures that necessary project details (folder, country, 
        and city) are set before execution. If AI-powered prediction is enabled, it 
        processes the images and updates the corresponding UI elements with the 
        predicted block position.
    
        Args:
            image_file (str): Path to the building image file to be analyzed.
    
        Effects:
            - Uses an AI model to predict the block position classification of the building.
            - Updates the UI combo boxes (`bck_pos_cb_1`, `bck_pos_cb_2`, `bck_pos_cb_3`) 
              with the predicted values.
            - Displays progress updates via the UI progress bar.
            - Handles both Google Street View (GSV) and local image-based inspections.
    
        Notes:
            - AI-based prediction is performed only if the AI checkbox (`ai_check`) is enabled.
            - In polygon-based and specific inspection modes (`insp_method != 2`), 
              cropped images are used for prediction.
            - For manual inspection mode (`insp_method == 2`), predictions are performed 
              on local cropped images.
            - The `predict_block_position_img` function is called to generate predictions.
            - The predicted index is incremented by 1 before being assigned to the combo box.
        """

        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            pass
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            pass
        else:
            # Comboboxes for each image label
            block_position_id = [self.ui.bck_pos_cb_1,self.ui.bck_pos_cb_2,self.ui.bck_pos_cb_3]
            # Checkbox for the AI powered activation
            if self.ui.ai_check.isChecked():
                if self.ui.insp_method !=2:
                    for i in range (3):
                        if self.predicted_img[i] == 1:
                            # Image path
                            image_file = self.cropped_image        
                            # block_position building image prediction
                            block_position_index = predict_block_position_img(image_file, self.ui.insp_method)
                            # block_position building image sets prediction
                            block_position_id[i].setCurrentIndex(block_position_index+1)                       
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")
                else:
                    
                    self.ui.method_progress.setText("Loading AI model ...")
                    for j in range (100):
                        time.sleep(0.0001)
                        self.ui.progress_bar_method.setValue(j)
                        
                    for aux in range (self.n_images_local):
                        # Local cropped image path
                        cropped_path = (self.ui.folder_path+"/Cropped_images/"
                                        +str(self.data_building.iloc[self.click_count * self.n_images_local + aux, 0])+"_cropped.jpg") 
                                     
                        
                        # block_position building image prediction
                        block_position_index = predict_block_position_img(cropped_path, self.ui.insp_method)
                        # block_position building image sets prediction
                        block_position_id[aux].setCurrentIndex(block_position_index+1)
          
                        # Peogress bar update
                        self.ui.progress_bar_method.setValue(100)
                        self.ui.method_progress.setText("Prediction complete!")      
              
                        
    ############ Search and load existing inspections ################                  
    def search_inspection(self):
        """
        Search for a specific building inspection record by its ID.
    
        This method retrieves a building inspection record from the dataset based on 
        the ID entered in the UI search field. It ensures that a project folder, country, 
        and city name are defined before execution. If the search value is empty, an 
        error message is displayed. If the inspection database is not loaded, the user 
        is prompted to upload it.
    
        Notes:
            - The search is performed on the `data_ai` DataFrame using the column 'ID'.
            - If no valid ID is entered, a message is set in the UI field instead of executing a search.
            - If the database is missing, the user is advised to upload it using the "Next Building" button.
        """

        # Conditional to avoid executing the method if there is no project folder
        if self.ui.output_folder_value.text() == "-":
            QMessageBox.warning(self.ui, "Project Error", "Please select project folder")
        # Conditional to avoid executing the method if there is no country name
        elif self.ui.country_value.text() == "-":
            QMessageBox.warning(self.ui, "Country Error", "Please sets country name")
        # Conditional to avoid executing the method if there is no city name 
        elif self.ui.city_value.text() == "-":
            QMessageBox.warning(self.ui, "City Error", "Please sets city name")
        else:
            # Get the value from the QLineEdit
            search_value = self.ui.search_img_value.text()
            # Check if the value is not empty
            if not search_value.strip():
                self.ui.search_img_value.setText("Please enter a value to search.")
                return

            # Search in the DataFrame
            try:
                result = self.data_ai[self.data_ai['ID'] == search_value]
            except:
                QMessageBox.warning(self.ui, "Data Error", "Please click the Next Building button to upload the inspection database")
            n_building = result.iloc[0,0][0]
            self.click_count = int(n_building)
