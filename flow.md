**🌐 System Flow of ScoutConnect**

ScoutConnect is a centralized web-based platform designed to manage **membership, communication, payments, and reporting** for the **Boy Scouts of the Philippines (BSP)** at the local council level. Here's a step-by-step breakdown of how the system flows and functions across different modules:

**1\. User Access and Role-Based Login**

-   **Users** such as **Scouts, Parents, Scoutmasters**, and **Administrators** visit the ScoutConnect website using a **desktop or mobile device**.
-   They are directed to a **login or registration page**:
    -   **New scouts** can **register online**, filling out digital forms for personal info, school/unit, parent/guardian contact, etc.
    -   **Admins** approve or verify new registrations.
-   The system applies **role-based access**:
    -   **Admins** have full control of data, announcements, payments, and reporting.
    -   **Scoutmasters** can manage members under their unit, post announcements, and track participation.
    -   **Scouts/Parents** can view announcements, update info, and monitor payments.

**2\. Registration & Membership Database**

-   Once registered, each member has a **digital profile** stored in a secure database.
-   Admins can:
    -   **View, update, or remove** member records.
    -   Assign scouts to specific **troops or units**.
    -   Monitor **badge progress, attendance**, and participation history.
-   This replaces manual spreadsheets with a **dynamic CRUD-enabled system** (Create, Read, Update, Delete).

**3\. Communication System**

-   Admins and scoutmasters can send **SMS and email announcements** directly from the platform:
    -   Event reminders
    -   Urgent updates
    -   Meeting notices or cancellations
-   The system uses **SMS API or email gateway** integration for **real-time communication**, reaching all members instantly without relying on bulletin boards or verbal messages.

**4\. Payment Tracking Module**

-   Scouts/parents can upload **proof of payment** (e.g., receipt images) for:
    -   Membership dues
    -   Uniform fees
    -   Event fees
-   Admins verify the payment and mark it as “**Confirmed**”.
-   The system stores all transactions in a **payment ledger**, generating:
    -   Individual payment history
    -   Outstanding balances
    -   Downloadable receipts
-   Although no online payment gateway is integrated (due to prototype limitations), the system simulates **digital tracking** efficiently.

**5\. Dashboard and Reports**

-   The system includes an **interactive dashboard** visible to admins and scoutmasters:
    -   **Graphs and charts** show active members, event participation, payment status, and more.
    -   Visuals are generated using **tools like Chart.js or similar libraries**.
-   Reports can be generated in **real-time**, helping leaders:
    -   Identify inactive members
    -   Plan events based on participation trends
    -   Make data-informed decisions

**6\. Security & Accessibility**

-   **Secure logins** protect each role (admin, scoutmaster, scout).
-   Data validation prevents errors like **duplicate entries or incorrect details**.
-   The system is **mobile responsive**, ensuring access via both **PC and smartphone** browsers.

**7\. Flow Example for a Typical Use Case:**

Imagine a new school year starting:

1. Scouts register online and upload documents.
2. Admins verify registration and assign them to units.
3. Parents upload payment proof for registration dues.
4. Scoutmasters send out SMS about the first troop meeting.
5. On the day of the event, scoutmasters take attendance online.
6. Admins generate a participation report at the end of the month.

**✅ 1. Do Parents Register Too?**

**No**, parents don't need to register **as separate users** in the system. Instead:

-   Parents **assist scouts** during **registration** (especially younger scouts).
-   The **scout's digital profile** will include **parent/guardian contact information** (like mobile number and email).
-   This allows the system to **send announcements** or **payment reminders** via SMS or email **to parents**, even if they don’t have their own login.

So, the system **focuses on scouts as users**, but it keeps **parents in the loop** by notifying them when:

-   Their child is registered or needs to complete requirements,
-   Payments are due or uploaded,
-   There are event announcements.

**💸 2. How Will They Pay Online?**

Since your system **doesn't include third-party payment gateways** (as noted in the delimitations), it will use a **simulated digital payment tracking** approach. Here's how it will work:

**🔁 Step-by-Step Payment Process:**

1. **Admin posts payment instructions** (e.g., amount for registration/uniform).
2. Parents will **send payment manually** through **GCash**, **Maya**, or **bank transfer** to the **BSP council’s official account or GCash number**.
3. The system will **display**:
    - GCash/Bank QR code (optional image upload)
    - GCash/Bank account name and number
    - Payment instructions
4. After paying, the **scout (or parent)** logs in and goes to the **"Upload Proof of Payment"** section.
5. They **upload a screenshot/photo** of the payment receipt.
6. The **admin verifies** the upload and marks it as:
    - ✅ Confirmed
    - ❌ Rejected (with remarks)

**📌 Example Interface: “Payment Section” (for Scouts/Parents)**

**Payment Instructions**

-   Amount Due: ₱500 (Membership)
-   GCash Name: Boy Scouts EVSU Council
-   GCash Number: 0917-123-4567
-   \[📷\] Upload GCash Screenshot
-   \[📤\] Submit for Verification

**🔒 Why This Approach Works for Now:**

-   No need to integrate secure payment APIs (like PayMongo or DragonPay) which may cost money or require business registration.
-   Easier for real-world parents to use **payment methods they're already familiar with**, like GCash.
-   Admins maintain **control over payment confirmation** before updating records.
