# SkuVault Picklist Generator

A portable Windows GUI application for generating picklists from SkuVault inventory data, designed specifically for showroom use at iDrinkCoffee.

## Features

- **Easy SKU Entry**: Type or scan barcodes directly into the application
- **Real-time Inventory Lookup**: Fetches current stock levels and locations from SkuVault
- **Location-based Organization**: Groups items by warehouse location for efficient picking
- **Visual Status Indicators**: 
  - Green highlighting for picked items
  - Red highlighting for low/out of stock items
- **Save/Load Picklists**: Save work in progress and reload later
- **Print-friendly Output**: Generate formatted picklists ready for printing
- **Secure Credential Storage**: API tokens are encrypted locally
- **No Installation Required**: Single .exe file that runs on any Windows PC

## Building the Application

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Build Steps

1. Navigate to the project directory:
```bash
cd /home/pranav/idc/tools/skuvault-picklist
```

2. Install required packages:
```bash
pip install requests cryptography pyinstaller
```

3. Run the build script:
```bash
python build.py
```

This will create:
- `dist/SkuVault Picklist.exe` - The standalone executable
- `dist/Launch SkuVault Picklist.bat` - Batch file for easy launching
- `SkuVault_Picklist_Installer/` - Folder with all files ready for distribution

## Deployment

### For Showroom Computers

1. Copy `SkuVault Picklist.exe` to the desktop or desired location
2. Create a desktop shortcut if desired
3. First run will prompt for API credentials

### API Credentials

The application requires SkuVault API credentials:
- **Tenant Token**: Your SkuVault tenant token
- **User Token**: Your SkuVault user token

These are entered once and stored encrypted locally.

## Usage

### Basic Workflow

1. **Launch the Application**: Double-click the .exe file
2. **Add Items to Picklist**:
   - Type or scan SKU into the input field
   - Press Enter or click "Add to Picklist"
   - Repeat for all items
3. **Generate Picklist**: Click "Generate Picklist" button
4. **Print or Save**: Use the print button or save as PDF

### Advanced Features

- **Bulk Add**: Click "Add Multiple" to paste a list of SKUs
- **Mark as Picked**: Right-click items and select "Mark as Picked"
- **Remove Items**: Right-click and select "Remove from List"
- **Save Session**: File → Save Picklist to save current work
- **Load Session**: File → Load Picklist to restore saved work

### Keyboard Shortcuts

- `Enter` in SKU field: Add to picklist
- `Right-click` on item: Show context menu

## Technical Details

### Architecture

- **GUI Framework**: Tkinter (built into Python, no external dependencies)
- **API Integration**: REST API calls to SkuVault
- **Data Storage**: Local config.ini file with encrypted credentials
- **Packaging**: PyInstaller creates single executable

### File Structure

```
skuvault-picklist/
├── main.py                 # Main GUI application
├── skuvault_api.py        # SkuVault API wrapper
├── build.py               # Build script
├── config.ini             # Settings (created on first run)
├── key.key                # Encryption key (created on first run)
└── assets/
    └── icon.ico           # Application icon (optional)
```

### API Endpoints Used

- `/api/products/getProducts` - Fetch product details
- `/api/inventory/getInventoryByLocation` - Get location data
- `/api/inventory/pickItemBulk` - Record picks (future feature)

### Security

- API credentials are encrypted using Fernet symmetric encryption
- Encryption key is stored locally in `key.key`
- No data is sent to external servers except SkuVault API

## Troubleshooting

### Application Won't Start
- Ensure Windows Defender isn't blocking the exe
- Try running as administrator
- Check for missing Visual C++ redistributables

### API Connection Failed
- Verify API credentials are correct
- Check internet connection
- Ensure SkuVault API is accessible

### SKU Not Found
- Verify SKU exists in SkuVault
- Check for typos or extra spaces
- Try the SkuVault product code instead

## Future Enhancements

- PDF export with proper formatting
- Barcode printing for pick labels
- Integration with label printers
- Mobile app version
- Multi-location picking optimization
- Integration with SkuVault pick sessions
- Inventory adjustment capabilities

## Support

For issues or feature requests, contact the IT department or create an issue in the project repository.