# autogauss 

Automated measurement scripting frontend for MC4000 xyz-stage + CH330 gaussmeter.

Developed because both contractors did ...less than spectacular jobs.
 
Uses pyautogui to interface with MC4000 GUI as no other viable avenue was identified.

CH330 gaussmeter has a correctly documented, albeit poorly designed serial interface. pyserial was used to interface with the gaussmeter. 