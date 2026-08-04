/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredswsmeta;

/**
 *
 * @author kim2
 */
public class RefactoredSWSMeta {

    public static void main(String[] args) {
        User user = new User("John Doe", "123456");

        if (user.authenticate("123456")) {
            Wallet usdWallet = user.addWallet("USD");  // Factory Method pattern
            Wallet eurWallet = user.addWallet("EUR");

            // Strategy pattern: execute transactions using different strategies
            TransactionStrategy depositStrategy = new DepositStrategy();
            usdWallet.executeTransaction(depositStrategy, 100);  // Deposit $100 to USD wallet

            TransactionStrategy paymentStrategy = new PaymentStrategy();
            usdWallet.executeTransaction(paymentStrategy, 25);  // Make a payment of $25 from USD wallet

            eurWallet.executeTransaction(depositStrategy, 200);  // Deposit €200 to EUR wallet

            // Singleton pattern: use the single instance of CurrencyConverter
            CurrencyConverter converter = CurrencyConverter.getInstance();
            double convertedAmount = converter.convert("EUR", "USD", 50);
            System.out.println("Converted €50 to $" + convertedAmount);

            user.showAllBalances();  // Show balances for all wallets
            usdWallet.showTransactions();  // Print USD wallet transaction history
            eurWallet.showTransactions();  // Print EUR wallet transaction history
        }
    }
}        
