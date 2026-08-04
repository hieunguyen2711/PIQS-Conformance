/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
public class RefactoredSWSClaude {

    public static void main(String[] args) {
        // Create factory
        WalletFactory factory = new StandardWalletFactory();
        
        // Create user with factory
        User user = new User("John Doe", "123456", factory);
        
        // Create and attach audit log observer
        AuditLog auditLog = new AuditLog();
        user.attach(auditLog);

        if (user.authenticate("123456")) {
            // Create wallets using factory method
            user.addWallet("USD");
            user.addWallet("EUR");

            Wallet usdWallet = user.getWallet("USD");
            Wallet eurWallet = user.getWallet("EUR");

            // Use strategy pattern for transactions
            usdWallet.executeTransaction("deposit", 100);  // Add $100 to USD wallet
            usdWallet.executeTransaction("payment", 25);   // Pay $25 from USD wallet
            eurWallet.executeTransaction("deposit", 200);  // Add €200 to EUR wallet

            // Use singleton currency converter
            double convertedAmount = CurrencyConverter.getInstance().convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            // Display results
            user.showAllBalances();
            usdWallet.showTransactions();
            eurWallet.showTransactions();
            
            // Show audit logs
            System.out.println("\nAudit Logs:");
            auditLog.showLogs();
        }
    }
}
