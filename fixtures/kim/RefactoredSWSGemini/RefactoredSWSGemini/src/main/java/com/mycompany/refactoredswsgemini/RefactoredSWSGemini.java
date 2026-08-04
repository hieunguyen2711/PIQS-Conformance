/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredswsgemini;

/**
 *
 * @author kim2
 */
public class RefactoredSWSGemini {

    public static void main(String[] args) {
        // Create a User with DefaultWalletFactory
        User user = new User("John Doe", "123456", new DefaultWalletFactory()); 

        // Register a ConsoleLogger with the AuditLog
        user.auditLog.addObserver(new ConsoleLogger()); 

        if (user.authenticate("123456")) {
            user.addWallet("USD");
            user.addWallet("EUR");

            Wallet usdWallet = user.getWallet("USD"); 
            Wallet eurWallet = user.getWallet("EUR");

            // Use DepositStrategy for initial funding
            usdWallet.addFunds(100); 
            eurWallet.addFunds(200); 

            // Make a payment using the default PaymentStrategy
            usdWallet.makePayment(25); 

            CurrencyConverter converter = CurrencyConverter.getInstance(); 
            double convertedAmount = converter.convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            user.showAllBalances();
            usdWallet.showTransactions();
            eurWallet.showTransactions();
        }
    }
}
