/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 * Click nbfs://nbhost/SystemFileSystem/Templates/Classes/Class.java to edit this template
 */
package com.mycompany.refactoredswsclaude;

/**
 *
 * @author kim2
 */
class StandardWalletFactory implements WalletFactory {
    @Override
    public Wallet createWallet(String currency) {
        return new Wallet(currency);
    }
}
// -------------------- Factory Method Pattern End --------------------
