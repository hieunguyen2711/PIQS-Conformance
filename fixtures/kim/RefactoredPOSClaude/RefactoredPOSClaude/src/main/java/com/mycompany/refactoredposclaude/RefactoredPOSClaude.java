/*
 * Click nbfs://nbhost/SystemFileSystem/Templates/Licenses/license-default.txt to change this license
 */

package com.mycompany.refactoredposclaude;

import java.util.Scanner;

/**
 *
 * @author kim2
 */
public class RefactoredPOSClaude {

    public static void main(String[] args) throws Exception {
        Scanner scan = new Scanner(System.in);
        
        System.out.println("Start");
        POS pos = new POS();
        
        Item i1 = new Item(1, "Milk  ", 3.79);
        Item i2 = new Item(2, "Banana", 1.49);
        Item i3 = new Item(3, "Apple ", 5.56);
        
        pos.addInventory(i1, 10);
        pos.addInventory(i2, 50);
        pos.addInventory(i3, 30);
        
        pos.startNewSale();
        
        pos.enterItem(i1, 2);
        pos.enterItem(i2, 3);
        pos.enterItem(i3, 1);
        
        pos.endSale();
        
        System.out.println("\nSelect Payment method (cash/credit card):");
        String paymentType = scan.nextLine();
        pos.makePayment(paymentType);
        
        scan.close();
    }
}
