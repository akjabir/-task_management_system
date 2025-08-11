Setup Instructions
1. Clone the repository
2. Create and activate a virtual environment
3. Install dependencies
4. Apply migrations
5. Create a superuser (for admin operations)
6. Run the development server
7. Access the API

*Overview of Key Features*

-User Registration and Authentication-

1. Users can register via the RegisterView API.
2. JWT authentication is used with customized token response that includes username and a success message.

-Author, Category, and Book Management-

1. Admin users manage authors, categories, and books through ModelViewSet endpoints.
2. Anyone can list and retrieve authors, categories, and books, but only admins can create, update, or delete.

-Borrowing Books-

1. Authenticated users can borrow books using BorrowAPIView.
2. Each user can have up to 3 active (not returned) borrowed books.
3. When a book is borrowed, available_copies of the book is decreased by 1.
4. Database transactions and select_for_update() are used to avoid race conditions.

-Returning Books-

1. Authenticated users return borrowed books via ReturnBookAPIView.
2. The return_date is set to the current time.
3. available_copies is increased by 1 on return.
4. If the return is late (after due_date), penalty points are assigned to the user.

-Penalty Points-

1. Late returns increment the user's penalty_points by the number of days late.
2. Penalty points are stored in a UserProfile linked to the user.
3. Users or staff can check penalty points via UserPenaltyPointsAPIView.

- Due Date Notifications-

1. A background task send_due_date_notifications can be triggered via SendDueNotificationsView.
2. This task sends notifications to users with books near due date (task implementation not shown here).

-Borrowing / Return Logic-

Borrowing:

1. User sends a POST request with book_id.
2. The system checks if the user already has 3 active borrows; if yes, the request is rejected.
3. The system locks the selected book row and checks if copies are available.
4. If available, a new borrow record is created, and available copies decrement by 1.

Returning:

1. User sends a POST request with borrow_id.
2. The system locks the borrow record and checks if the book is already returned.
3. Sets the return_date to now.
4. Increments the book's available copies by 1.
5. If returned after the due date, penalty points are added for each day late.

-Penalty Points Calculation-

1. Penalty points = number of days late after the due date.
2. Stored in a UserProfile model linked to the user.
3. Points accumulate over time with multiple late returns.

-Assumptions and Known Limitations-

1. Maximum 3 active borrows per user is hardcoded.
2. The due date logic and notification background task are assumed to exist (implementation not shown).
3. No partial book return or renewal logic.
4. No detailed notification system or email sending shown here. But I send terminal message testing perpose for security concern 
5. No rate limiting or advanced permissions beyond admin and authenticated users.
6. This system assumes all books and users are correctly managed in the database.
7. No pagination or advanced search filtering is implemented beyond basic search by author/category names.

Implement API rate limiting (per user): I set it but I could not enough time to check properly
