/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredswschatgpt;

/**
 *
 * @author kim2
 */
public class RefactoredSWSChatGPT {

    public static void main(String[] args) {
        AuditLog auditLog = new AuditLog();
        User user = new User("John Doe", "123456", auditLog);
        if (user.authenticate("123456")) {
            user.addWallet("USD");
            user.addWallet("EUR");

            Wallet usdWallet = user.getWallet("USD");
            Wallet eurWallet = user.getWallet("EUR");

            // Using Strategy Pattern for transactions
            usdWallet.processTransaction(100, "Deposit", new AddFundsStrategy());  // Add $100 to the USD wallet
            usdWallet.processTransaction(25, "Payment", new MakePaymentStrategy());  // Make a payment of $25 from USD wallet
            eurWallet.processTransaction(200, "Deposit", new AddFundsStrategy());  // Add €200 to the EUR wallet

            double convertedAmount = CurrencyConverter.getInstance().convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            user.showAllBalances();  // Show balances for all wallets
            usdWallet.showTransactions();  // Print USD wallet transaction history
            eurWallet.showTransactions();  // Print EUR wallet transaction history
        }
    }
}
