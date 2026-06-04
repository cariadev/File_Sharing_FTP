# File_Sharing_FTP
# File Sharing System using TCP & FTP

## Introduction

This project implements a File Sharing System based on the Client–Server architecture using Python. The system combines TCP and FTP protocols to provide reliable communication and efficient file transfer between clients and the server.

## Features

### User Features

* User registration and login
* File upload (free or paid)
* Browse approved files
* Download free files
* Purchase paid files
* View transaction history
* OTP email verification
* Wallet balance management

### Admin Features

* User management
* File approval/rejection
* Activity monitoring
* Revenue statistics
* Revenue distribution management

## Technologies Used

* Python 3.11
* TCP Socket Programming
* FTP Protocol
* Flask
* SQLite
* HTML/CSS
* Email OTP Authentication

## System Architecture

The system follows the Client–Server model:

* **TCP Server**

  * Handles authentication
  * Processes client requests
  * Manages transactions and communication

* **FTP Server**

  * Handles file upload/download
  * Manages shared file storage

* **Web Admin**

  * User management
  * File approval
  * Revenue monitoring

* **Client Application**

  * File sharing interface
  * Upload/download operations
  * Transaction management

## Project Structure

```text
FTP_File/
├── server/
│   ├── auth.py
│   ├── db.py
│   ├── ftp_server.py
│   ├── tcp_server.py
│   ├── handlers.py
│   └── models.py
├── web/
│   ├── templates/
│   └── __pycache__/
├── app.py
├── requirements.txt
└── README.md
```

## Installation

```bash
git clone https://github.com/cariadev/File_Sharing_FTP.git
cd File_Sharing_FTP
```

Create virtual environment:

```bash
python -m venv venv
```

Activate environment:

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run Project

### Start Server

```bash
python app.py
```

### Start Client

```bash
python client.py
```

### Start Admin Web

Open browser:

```text
http://localhost:5000
```

## Main Protocols

### TCP

* Authentication
* Command processing
* Client–Server communication
* Transaction handling

### FTP

* File upload
* File download
* File storage management
* Large file transfer

## Future Improvements

* Secure file transfer using FTPS
* End-to-end encryption
* Cloud storage integration
* Multi-server deployment
* Real-time notifications

## Author

**Lê Thị Kiều Loan**
VKU – Vietnam-Korea University of Information and Communication Technology

## License

This project is developed for educational and research purposes.
