okay. so we are going to be making a standalone desktop app that supports windows 10/11 and linux only. the app is called 'SC Dossier'. it is going to be a python based app and should have a very rich ui system that is built with tinkiter or pyqt6 or pygame or something.



\- the app shall have a constant tray icon and context menu presence

\- the apps default ui state will be a small overlay slip toolbar that attaches/snaps to the edge of screen and can be placed and pinned to exact location user desires, but must remain always snapped to edge of screen. this toolbar will have two buttons on it only, these shouuld use high quality scg icons, one of these will be to toggle/expand our tool bar out from the position of the toolbar to display our main window which will hide the toolbar. the main window should not have the typical window controls on the custom titlebar but instead shouuld have a pin button and a hide button, the pin will force the window to stay topmost and not allow collapsing the window while pinned. the hide button control will collapse and hide the main window back down to the toolbar making the toolbar visible again.

\- the second button on our toolbar will be to enter a snapshot mode where user can use mouse to click and drag to create a box anywhere on screen to select a region on screen space to take screenshot of text on the screen, which we will then extract the text from and convert it into a text string which we will use as an alternative method to typing a player name into the search to lookup a players dossier. this way they can click the toolbar button, we enter capture mode and capture the region anywhere on the screen the user might see the player we want to search for might have their name visible.



DETAILS:

so the main purpose of this app will be to a standalone app/tool for the game Star Citizen, its job will be to retreive information about players (and their associated org details), and orgs, and give user ways to archive searched player profiles for later viewing and also auto sync of already archiverd profiles to keep information and or changes to online data uupdated to archived profiles, extract their profile informations or org informations to a json, txt, html, csv or whatever would make most sense



so the way this needs to work is we will need to create a highly sophisticated core and services that include a complex and very precise, accurate and effective scraper to scrape all of our needed details, badge images, org images, player avatar images, and all all the various detailsl that are ACTUUALLY available for a player or org and place it into a temp cache organized by playernames that we use for populating our ui with the retreived information and images. also if user chooses to archive the profile we need to then use the temp gathered information to build an archive dir location organized by player name which has our profile .json which contains al the text details we will need store all the information we gather related to the player and to fill out ui details from as well as to store the downloaded images that are belonging to the player profile for the avatar, badges, org logo/avatar images, acheivements.... etc.... all of which will be scraped from the rsi dossier website upon retreival.



\- the idea is so that the app will have a default state being the very compact and low profile toolbar that snapps to the edge of the screen as an overlay (forced to be topmost always) that will be present as user plays the game, if they want to easily look at information about a user they can click the first button on the toolbar that expands out to the apps main window and hides toolbar while main is visible, and when user is not interacting with main window they can click hide button which will collapse it back into our toolbar and make the toolbar visible once more.

\- the second button on the toolbar is to make a super easy simplified handy way for if user wants to check out a player, they can click it and the app goes into a focused screen region capture mode which is controlled by user mouse click and drag to place a selection box on screen and size to to the shape and pos on the exact region of the screen that the user seees the playername of interest, this will snap a screenshot of that exact region capturing the text of playername, stores temp, then uses it with a reader/extraction service we will implement that is acccurate and local and this will extract the user name, if there is issue extracting the string or if text is not found in shot prompt a dialog but if string can succesfully be extracted we will use this string to initiate a player dossier profile search. its process should: hide toolbar > open/show main window and navigate to search tab instert the extracted playername string and initiate search > before actually starting the scraping service, check playername against local archive, if found in archive we load this information and then check the live site to see if we neeed to perform a sync operation to update archived profile info > if not archived then retreive all player or org data from live site and store temp location and use for display on ui (if user manually types a username to search for then this will all still work the same but without the screen capture and extraction steps)



\- the live rsi dossier site we will be building our scraper to focus on will be:

https://robertsspaceindustries.com/en/citizens/\*playername\*



\- complete details for associated orgs will be found:

https://robertsspaceindustries.com/en/citizens/\*playername\*/organizations



however, it is absolutely crucial that you very deeply examine the actual site data thoroughly so that you truly and fullly have understanding of what details on the dossier we can actually realistically gather and store, and how we neeed to scrape it all. so for this purpose here the dossier of my actual player in star citizen, this will allow properly studying as well as a means for testing and confirmations of our service working properly:

https://robertsspaceindustries.com/en/citizens/PINKgeekPDX



you will also neeed to be building a seperate scraping service for organizations lookups and data/image gatherings that very much as critical as the player scraping service very much just as important, and will use the same processes of temp storage but we wont be archiving data for standalone organization searches, only temp for purpose of loading and viewing in app ui organization tab. note: dont confuse and of this though as its totally uunrelated to player lookups which will also gather orgs informations details and images for asssociated to the p\[layer orgs and those details and images WILL be handled in temp and also with storing for archived profiles in same location as the oplayer data and images locations and retreived amnd displayed in dossier tab with the players information and etc... anyways the seperate organizations scraper service will be using this rsi live site to gather informations:

(note: it might be tricky but we neeed to find a way to make the organization search feature work intuitively but, the rsi page expects an org sid which is not the same as the listing for the org name in some cases, however i want our users to be able to not need to know the org sid when typing to search the org, they shoild be able to find it by either the name of org or the sid! so you willl neeeed to carefullly analyze and consider approaches for this that will be best tand allow us to do this!)



> live rsi to scrape:

https://robertsspaceindustries.com/en/orgs/\*org-sid\*

&#x20;

> the is the full complete orgs ledger/list, im providing this incase perhaps it may be useful to figure out a way to find the org sid by providing the org name when we initiate a search processs for organization from our app:

https://robertsspaceindustries.com/en/community/orgs/listing



ALSO for the same purpose of testing and confirmations reason i provided the live page of my asctual player profile dossier, here i am also providing you my actual live rsi org page that is associated with my player profile dossier page i gave you already:

https://robertsspaceindustries.com/en/orgs/THEKVLT



also, ive already explained to you the framework and ui methpods we will be using, however ive always provided some files that are strictly to serve you as a means of example to understand more or less the look/style/theme and content layout, effects, animations that i want and require this app ui to use, it neeeds to be heavily influenced by the eample ui im providing (this example ui is not using same framework as our app requuires, however you cam use this to understand the goals and design aspects im asking for). this design/theme/styling must be consistently used and implemented throughout the entire app and all things related to ui/ux... so all windows/views (which use a fuuully custom title bar with click drag to reposition ability and custom statusbar, and left side nav bar which works like tabs. the window should be resizeable but have min max constrains and not allow being maximized. the main window will not have exit or close buttons and only a hide button to return to the apps default toolbar state/visibility), overlay/toolbar, buttons, widgets, dialogs, warning messages, elements, etc.. you will find these example/influence ui files here (there will also be a 'image.png' file found here which will show you a screenshot of the design example for visual examination):

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\ui-example-files



the root of our project workspace is here: 

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier



the codebase containing all parts of codebase, ui, assets and tests will all be created here, and be very properly organized and intuuuitively structured using naming conventions that are common sense and follow typical industry standards. this will located here:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\src



> NOTE: main window requirment <:

the main windows neeeds to have tab navs and content areas for: 



\- Search:

this is more of an action button but still on the top of the tab nav buttons, this shows two controls: search player and search org, if player is selected it shouuuld switch to the dossier tab but instead of showing the normal dossier elements, show the search elements to search for player name, it can have a search box and controls. if its organization selected switch to the organizations tab and dont show normal orgs elements, show the search elements similar to the player routine. upon entering the search keywords for both of these, it will handle the processses of finding scraping downloading and retreiving all neeeded data to display and it will then hide search progress elements and instead show the intended ui elements within the tab content area that is neeeded and intended to be filled for displaying all the details and imaghes. this case for both dossier and organizations tab (NOTE: dossier tab will also contain elements for showing all org(s) \*if more then one is found\* details associated to and agathered that are associated to the specific player. The organizations tab and content area is specifcally for gathering and displaying ONLY org information scraped from rsi page.) anyways....  when app is first opened or showing main window first ttime the search tab with its two controls for choosing to search a player or an org should be the default shown tab at first open for app session but otherwise when main window is shown maintain persistently showing the tab and content last used upon main window being hidden/collapsed.



\- Dossier:

please make sure the elements used here are ONLY showing and trying to be visualizing ALL realistic/real/possible data and actual real downloaded pics for avatar and badges and org logo for player that is found on the rsi dossier site from scraping 



\- Organization:

this has the same requirements of ONLY displaying real obtainable actual data provided on the tsi site and scraped



\- Archive:

this tab and content area will have two panes (the list pane which should have a button to collapse it or shrink it to allow more window space to be used by second pane. second pane is area with all the needed elements justlike the ones used on the dossier tab to fill and display all the stored information and images related to the selected in list playername)  show a full and very clean and intuitive list of all player profiles that are stored in our appdata location, selecting a name in the list will display. this list should be very clean and readable and organized while offering controls for filtering and sorting. this tab also needs to include per profile controls for sync check, deleting the profile  and all its files from archive list and storage location and an extract profile button for extracting details and images and building a zip (placed on desktop) that contains profile content: avatar, other images used, a text file with all the players and associated orgs informatiomn, a html file including a stylized standalone page that uses the media and json file in the zip to display a card with a;l the players information) for extraction to zip and easy send to friend or use later purpose. 

> NOTE: all docs files should use .md <



all finalized docuumentation/app use instructiomns/readmes/wikis and etc will be generated here:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\docs\\docuuumentation



all work (past/current/future) related docs generated should go:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\docs\\work

> todo: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\docs\\work\\todo

> summaries: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\docs\\work\\summaries

> reports: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\docs\\work\\reports



all build related scripts for our supported dist types shouuld be here:

> windows 10/11 binary: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\build\\windows

> linux deb/mint/ubuntu/arch: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\build\\linux\\\*distro\*\\\*



all built results (binaries and any resources neeeded):

> windows 10/11 binary: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\built\\dist\\windows

> linux deb/mint/ubuntu/arch: C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\built\\dist\\linux\\\*distro\*\\\*



all specific purpose or single case use scripts/tools/pipelines need to ONLY be generated here AND ONLY HERE, DO NOT generate them into our project root EVER please!:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\scripts\\tools\\\*



runner scripts to start our app and run it from code for testing/debuggiong throghout the dev process can just be stored here:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\scripts\\\*



all logs generated by purpose scripts, tools or tests throughout dev must be generated here ( NOT APP ROOT ):

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\logs\\\*



all project files, spec files and repo/project readme.md as well as agent.md files are to be generated at project root:

C:\\Users\\Administrator\\Desktop\\projects\\SCDossier\\\*



all logging generated by our apps normal running functionality as well as any settings.json files (all settings as well as screen size and pos of main window amnd the position of the toolbar overlay that is pinned/set by user must all be persistent between app sessions and show/hiding or expand/collapse states) and fyi there will neeed to be a comprehensive settings tab on the main window that allows configuration of the app very comprehensively, all changes to settings values should trigger them to auto be saved and applied/updated. and also ALLL the temp profile date that we scrape when we search for profile of player (that we are not archived) as well as the archived profiles location will alll use these locations and app must be CEERTIAMN to be consistent with the throughout all parts. the locations for all these (remember all these paths are being shown as windows, for the linux support it woouuld be whatever is the equivalint for linux):



> main settings.json: 

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Config\\\*



> app running logs/error logs: 

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Logs\\\*



> temp player profile download cache:

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Cache\\Temp\\\*playername\*\\\*image-name\*.png (for all images used with player dossier)

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Cache\\Temp\\\*playername\*\\\*extracted-text-info.json\*



> cache to store all archived profile data:

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Cache\\Archived\\\*playername\*\\\*image-name\*.png (for all images used with player dossier)

Users\\\*user\*\\Documents\\PINK\\SCDossier\\Cache\\Archived\\\*playername\*\\\*extracted-text-info.json\*

