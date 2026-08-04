/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredswscopilot;

/**
 *
 * @author kim2
 */
public class RefactoredSWSCopilot {

    public static void main(String[] args) {
        WalletFactory walletFactory = new ConcreteWalletFactory();
        User user = new User("John Doe", "123456", walletFactory);
        if (user.authenticate("123456")) {
            user.addWallet("USD");
            user.addWallet("EUR");

            Wallet usdWallet = user.getWallet("USD");
            Wallet eurWallet = user.getWallet("EUR");

            TransactionStrategy addFundsStrategy = new AddFundsStrategy();
            TransactionStrategy makePaymentStrategy = new MakePaymentStrategy();

            System.out.println(usdWallet.performTransaction(100, addFundsStrategy));  // Add $100 to the USD wallet
            System.out.println(usdWallet.performTransaction(25, makePaymentStrategy));  // Make a payment of $25 from USD wallet
            System.out.println(eurWallet.performTransaction(200, addFundsStrategy));  // Add €200 to the EUR wallet

            double convertedAmount = CurrencyConverter.getInstance().convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            user.showAllBalances();  // Show balances for all wallets
            usdWallet.showTransactions();  // Print USD wallet transaction history
            eurWallet.showTransactions();  // Print EUR wallet transaction history

            AuditLog auditLog = user.getWallet("USD").addObserver(auditLog);  // Print audit logs
        }
    }
}
